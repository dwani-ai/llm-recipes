import math
import torch
import torch.nn as nn
import torch.nn.functional as F


def precompute_freqs_cis(
    dim: int,               # usually head_dim
    max_seq_len: int,
    theta: float = 10000.0, # Llama-2/3 uses 10000 or higher (Llama-3 uses 500000 for long ctx)
    device: torch.device = None,
) -> torch.Tensor:
    """Precompute complex exponential frequencies for RoPE."""
    freqs = 1.0 / (theta ** (torch.arange(0, dim, 2, device=device).float() / dim))
    t = torch.arange(max_seq_len, device=device, dtype=torch.float32)
    freqs = torch.outer(t, freqs).float()  # [seq_len, dim/2]
    freqs_cos = freqs.cos()                # [seq_len, dim/2]
    freqs_sin = freqs.sin()                # [seq_len, dim/2]
    # Complex form for multiplication
    return torch.complex(freqs_cos, freqs_sin)  # [max_seq_len, dim/2]


def apply_rotary_emb(
    x: torch.Tensor,          # [..., seq_len, dim]  (usually [b, heads, seq, head_dim])
    freqs_cis: torch.Tensor,  # [seq_len, head_dim//2]
) -> torch.Tensor:
    """Apply rotary positional embeddings to queries/keys."""
    # Reshape last dim to pairs: [..., seq, head_dim//2, 2] → view as complex
    x_ = torch.view_as_complex(x.float().reshape(*x.shape[:-1], -1, 2))
    # Broadcast freqs_cis to match shape
    freqs_cis = freqs_cis.view(1, 1, x_.shape[2], x_.shape[3])  # add batch & heads dims
    # Rotate in complex plane
    x_out = x_ * freqs_cis
    # Back to real + imag → flatten pairs
    return torch.view_as_real(x_out).flatten(-2).type_as(x)


class RotaryEmbedding(nn.Module):
    """RoPE module — precomputes frequencies and applies rotation."""
    def __init__(
        self,
        head_dim: int,
        max_seq_len: int = 8192 * 4,  # generous default (32k+)
        theta: float = 10000.0,
    ):
        super().__init__()
        self.head_dim = head_dim
        self.max_seq_len = max_seq_len
        self.theta = theta

        # Precompute once
        self.register_buffer(
            "freqs_cis",
            precompute_freqs_cis(head_dim, max_seq_len, theta),
            persistent=False,
        )

    def forward(
        self,
        x: torch.Tensor,
        seq_len: int | None = None,
        position_ids: torch.Tensor | None = None,
    ) -> torch.Tensor:
        """Apply RoPE to x (q or k)."""
        if seq_len is None:
            seq_len = x.shape[-2]  # assume last dim before head_dim is seq

        # Slice precomputed freqs (supports cache: only new positions)
        if position_ids is not None:
            # Advanced: use arbitrary position ids (e.g. for packed or non-sequential)
            freqs = self.freqs_cis[position_ids].to(x.device)
        else:
            # Standard: 0 → seq_len-1
            freqs = self.freqs_cis[:seq_len].to(x.device)

        return apply_rotary_emb(x, freqs)


class GroupedQueryAttentionWithCacheAndRoPE(nn.Module):
    """
    GQA + KV cache + Rotary Positional Embeddings (RoPE).
    """
    def __init__(
        self,
        embed_dim: int,
        num_heads: int,
        num_kv_heads: int,
        head_dim: int = None,
        max_seq_len: int = 8192 * 4,
        rope_theta: float = 10000.0,   # Llama-3 uses 500000 for better long-context
        dropout: float = 0.0,
        bias: bool = True,
    ):
        super().__init__()
        self.embed_dim = embed_dim
        self.num_heads = num_heads
        self.num_kv_heads = num_kv_heads
        self.head_dim = head_dim or (embed_dim // num_heads)
        self.dropout_p = dropout

        assert embed_dim % num_heads == 0
        assert num_heads % num_kv_heads == 0

        # Projections
        self.q_proj = nn.Linear(embed_dim, num_heads * self.head_dim, bias=bias)
        self.k_proj = nn.Linear(embed_dim, num_kv_heads * self.head_dim, bias=bias)
        self.v_proj = nn.Linear(embed_dim, num_kv_heads * self.head_dim, bias=bias)
        self.out_proj = nn.Linear(num_heads * self.head_dim, embed_dim, bias=bias)

        self.repeat_factor = num_heads // num_kv_heads

        # RoPE
        self.rotary_emb = RotaryEmbedding(
            head_dim=self.head_dim,
            max_seq_len=max_seq_len,
            theta=rope_theta,
        )

    def forward(
        self,
        x: torch.Tensor,                        # [b, seq_len, embed_dim]
        past_key_value: tuple[torch.Tensor, torch.Tensor] | None = None,
        position_ids: torch.Tensor | None = None,  # [b, seq_len] or [b, 1] in decode
        attn_mask: torch.Tensor | None = None,
        is_causal: bool = True,
        return_weights: bool = False,
    ):
        b, s, _ = x.shape

        q = self.q_proj(x)
        k = self.k_proj(x)
        v = self.v_proj(x)

        q = q.view(b, s, self.num_heads, self.head_dim)
        k = k.view(b, s, self.num_kv_heads, self.head_dim)
        v = v.view(b, s, self.num_kv_heads, self.head_dim)

        # Apply RoPE to Q and K (V is not rotated)
        # In decode mode: position_ids usually = [past_len] for the new token
        q = self.rotary_emb(q, seq_len=s, position_ids=position_ids)
        k = self.rotary_emb(k, seq_len=s, position_ids=position_ids)

        # Cache handling
        if past_key_value is not None:
            past_k, past_v = past_key_value
            k = torch.cat([past_k, k], dim=1)
            v = torch.cat([past_v, v], dim=1)
            new_past_key_value = (k, v)
        else:
            new_past_key_value = (k, v)

        total_seq_len = k.shape[1]

        # Repeat K/V for GQA
        k = k.repeat_interleave(self.repeat_factor, dim=2)
        v = v.repeat_interleave(self.repeat_factor, dim=2)

        # Transpose → [b, heads, seq, d]
        q = q.transpose(1, 2)
        k = k.transpose(1, 2)
        v = v.transpose(1, 2)

        # Scaled dot-product
        attn_weights = torch.matmul(q, k.transpose(-2, -1)) / math.sqrt(self.head_dim)

        if is_causal:
            causal_mask = torch.triu(
                torch.full((total_seq_len, total_seq_len), float("-inf"), device=x.device),
                diagonal=1
            )
            causal_mask = causal_mask[None, None, -s:, :]
            attn_weights = attn_weights + causal_mask

        if attn_mask is not None:
            attn_weights += attn_mask

        attn_weights = F.softmax(attn_weights, dim=-1)
        if self.dropout_p > 0 and self.training:
            attn_weights = F.dropout(attn_weights, p=self.dropout_p)

        out = torch.matmul(attn_weights, v)
        out = out.transpose(1, 2).contiguous().view(b, s, -1)
        out = self.out_proj(out)

        if return_weights:
            return out, new_past_key_value, attn_weights
        return out, new_past_key_value


# ────────────────────────────────────────────────────────────────
#   Quick test / usage example
# ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    device = "cuda" if torch.cuda.is_available() else "cpu"
    torch.manual_seed(0)

    batch_size, embed_dim = 2, 512
    num_heads, num_kv_heads = 8, 2
    seq_len = 64

    model = GroupedQueryAttentionWithCacheAndRoPE(
        embed_dim=embed_dim,
        num_heads=num_heads,
        num_kv_heads=num_kv_heads,
        max_seq_len=8192,
        rope_theta=500000.0,   # like Llama-3 for long-context support
    ).to(device)

    x = torch.randn(batch_size, seq_len, embed_dim, device=device)
    position_ids = torch.arange(seq_len, device=device).expand(batch_size, seq_len)

    out, past_kv = model(x, position_ids=position_ids, is_causal=True)
    print("Output shape:", out.shape)               # [2, 64, 512]
    print("KV cache seq len:", past_kv[0].shape[1]) # 64

    # Simulate decode: one token
    x_new = torch.randn(batch_size, 1, embed_dim, device=device)
    pos_new = torch.tensor([[seq_len]], device=device)  # next position
    out_new, past_kv = model(
        x_new,
        past_key_value=past_kv,
        position_ids=pos_new,
        is_causal=True,
    )
    print("Decode output shape:", out_new.shape)     # [2, 1, 512]
    print("Updated cache len:", past_kv[0].shape[1]) # 65