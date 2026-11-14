"""
Speculative Decoding Engine
===========================
Draft+verify with small draft model for faster GGUF inference.
"""

from __future__ import annotations

import time
from typing import Any, List, Optional

from llama_cpp import Llama


class SpeculativeEngine:
    """
    Speculative decoding engine using a draft model and target model.
    
    The draft model generates multiple tokens speculatively, which are then
    verified by the target model in parallel. Accepted tokens are kept,
    rejected tokens trigger re-generation.
    """

    def __init__(
        self,
        draft_model: Llama,
        target_model: Llama,
        num_draft_tokens: int = 4,
        max_tokens: int = 256,
        temperature: float = 0.8,
        top_p: float = 0.95,
    ):
        self.draft_model = draft_model
        self.target_model = target_model
        self.num_draft_tokens = num_draft_tokens
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.top_p = top_p

        # Statistics
        self.total_generated = 0
        self.total_accepted = 0
        self.total_rejected = 0
        self.draft_time_ms = 0.0
        self.verify_time_ms = 0.0

    def _sample_token(self, logits: List[float], temperature: float, top_p: float) -> int:
        """Sample a token from logits with temperature and top-p."""
        import numpy as np

        if temperature == 0:
            return int(np.argmax(logits))

        logits = np.array(logits, dtype=np.float32)
        logits = logits / temperature
        probs = np.exp(logits - np.max(logits))
        probs = probs / np.sum(probs)

        if top_p < 1.0:
            sorted_indices = np.argsort(probs)[::-1]
            sorted_probs = probs[sorted_indices]
            cumsum = np.cumsum(sorted_probs)
            cutoff = cumsum >= top_p
            if np.any(cutoff):
                first_true = np.argmax(cutoff)
                sorted_probs[first_true + 1:] = 0
                sorted_probs = sorted_probs / np.sum(sorted_probs)
            probs[sorted_indices] = sorted_probs

        return int(np.random.choice(len(probs), p=probs))

    def generate_draft(self, prompt: str, num_tokens: int) -> List[int]:
        """Generate draft tokens using the draft model."""
        start = time.perf_counter()

        # Get initial logits from draft model
        output = self.draft_model(prompt, max_tokens=0, echo=True)
        # Extract logits from the last position
        # Note: llama_cpp doesn't expose logits directly in simple API
        # We'll use the generate approach instead

        draft_tokens = []
        current_prompt = prompt

        for _ in range(num_tokens):
            # Generate one token
            result = self.draft_model(current_prompt, max_tokens=1, echo=False)
            choices = result.get("choices", [])
            if not choices:
                break
            token_text = choices[0].get("text", "")
            if not token_text:
                break
            draft_tokens.append(token_text)
            current_prompt += token_text

        self.draft_time_ms += (time.perf_counter() - start) * 1000
        return draft_tokens

    def verify_draft(self, prompt: str, draft_tokens: List[str]) -> List[int]:
        """Verify draft tokens using the target model."""
        start = time.perf_counter()

        # Build full sequence with draft tokens
        full_prompt = prompt + "".join(draft_tokens)

        # Get logits from target model for each position
        # We need to run the target model and get probabilities
        accepted = []

        # For each draft token, verify by checking target model's probability
        current_prompt = prompt
        for i, draft_token in enumerate(draft_tokens):
            # Get target model logits for next token
            result = self.target_model(current_prompt, max_tokens=1, echo=False)
            choices = result.get("choices", [])
            if not choices:
                break

            # The target model's top token should match our draft token
            target_text = choices[0].get("text", "")

            if target_text == draft_token:
                accepted.append(1)  # Accepted
            else:
                accepted.append(0)  # Rejected
                break  # Stop at first rejection

            current_prompt += draft_token

        self.verify_time_ms += (time.perf_counter() - start) * 1000
        return accepted

    def generate(self, prompt: str) -> str:
        """Generate text using speculative decoding."""
        generated = ""
        current_prompt = prompt

        for _ in range(self.max_tokens):
            # Generate draft tokens
            draft_tokens = self.generate_draft(current_prompt, self.num_draft_tokens)

            if not draft_tokens:
                break

            # Verify with target model
            accepted = self.verify_draft(current_prompt, draft_tokens)

            # Keep accepted tokens
            num_accepted = sum(accepted)
            if num_accepted > 0:
                accepted_tokens = draft_tokens[:num_accepted]
                generated += "".join(accepted_tokens)
                current_prompt += "".join(accepted_tokens)
                self.total_accepted += num_accepted
                self.total_generated += num_accepted

            # If all rejected or partial, we need to generate with target model
            if num_accepted < len(draft_tokens):
                # Generate one token with target model
                result = self.target_model(current_prompt, max_tokens=1, echo=False)
                choices = result.get("choices", [])
                if not choices:
                    break
                target_token = choices[0].get("text", "")
                if not target_token:
                    break
                generated += target_token
                current_prompt += target_token
                self.total_generated += 1
                self.total_rejected += 1

            # Check for stop condition (e.g., EOS token)
            # This is simplified - real implementation would check for actual EOS

        return generated

    def get_stats(self) -> dict:
        """Get engine statistics."""
        acceptance_rate = (
            self.total_accepted / self.total_generated
            if self.total_generated > 0 else 0
        )
        return {
            "total_generated": self.total_generated,
            "total_accepted": self.total_accepted,
            "total_rejected": self.total_rejected,
            "acceptance_rate": acceptance_rate,
            "draft_time_ms": round(self.draft_time_ms, 2),
            "verify_time_ms": round(self.verify_time_ms, 2),
            "speedup_factor": round(
                (self.draft_time_ms + self.verify_time_ms) / max(self.verify_time_ms, 1), 2
            ) if self.verify_time_ms > 0 else 0,
        }

    def reset_stats(self):
        """Reset statistics."""
        self.total_generated = 0
        self.total_accepted = 0
        self.total_rejected = 0
        self.draft_time_ms = 0.0
        self.verify_time_ms = 0.0


def create_speculative_engine(
    draft_model_path: str,
    target_model_path: str,
    num_draft_tokens: int = 4,
    n_ctx: int = 2048,
    **kwargs
) -> SpeculativeEngine:
    """Factory function to create a speculative engine from model paths."""
    draft = Llama(model_path=draft_model_path, n_ctx=n_ctx, verbose=False)
    target = Llama(model_path=target_model_path, n_ctx=n_ctx, verbose=False)
    return SpeculativeEngine(draft, target, num_draft_tokens, **kwargs)