import math
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.backends.cuda import sdpa_kernel, SDPBackend


def precompute_freqs_cis(
    dim: int,
    max_seq_len: int,
    theta: float = 10000.0,
    device: torch.device = None,
) -> torch.Tensor:
    """Precompute complex exponential frequencies for RoPE."""
    freqs = 1.0 / (theta ** (torch.arange(0, dim, 2, device=device).float() / dim))
    t = torch.arange(max_seq_len, device=device, dtype=torch.float32)
    freqs = torch.outer(t, freqs).float()
    freqs_cos = freqs.cos()
    freqs_sin = freqs.sin()
    return torch.complex(freqs_cos, freqs_sin)


def apply_rotary_emb(
    x: torch.Tensor,          # [..., seq_len, dim]
    freqs_cis: torch.Tensor,  # [seq_len, dim//2]
) -> torch.Tensor:
    x_ = torch.view_as_complex(x.float().reshape(*x.shape[:-1], -1, 2))
    freqs_cis = freqs_cis.view(1, 1, x_.shape[2], x_.shape[3])
    x_out = x_ * freqs_cis
    return torch.view_as_real(x_out).flatten(-2).type_as(x)


class RotaryEmbedding(nn.Module):
    def __init__(
        self,
        head_dim: int,
        max_seq_len: int = 32768,
        theta: float = 10000.0,
    ):
        super().__init__()
        self.head_dim = head_dim
        self.max_seq_len = max_seq_len
        self.theta = theta
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
        if seq_len is None:
            seq_len = x.shape[-2]
        if position_ids is not None:
            freqs = self.freqs_cis[position_ids].to(x.device)
        else:
            freqs = self.freqs_cis[:seq_len].to(x.device)
        return apply_rotary_emb(x, freqs)


class GroupedQueryAttentionFlash(nn.Module):
    """
    GQA + KV cache + RoPE + Flash Attention (via SDPA).
    Uses torch.nn.functional.scaled_dot_product_attention with enable_gqa=True.
    """
    def __init__(
        self,
        embed_dim: int,
        num_heads: int,
        num_kv_heads: int,
        head_dim: int = None,
        max_seq_len: int = 32768,
        rope_theta: float = 10000.0,   # Llama-3 style: 500000 for long ctx
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
        assert num_heads % num_kv_heads == 0, "num_heads must be divisible by num_kv_heads"

        self.q_proj = nn.Linear(embed_dim, num_heads * self.head_dim, bias=bias)
        self.k_proj = nn.Linear(embed_dim, num_kv_heads * self.head_dim, bias=bias)
        self.v_proj = nn.Linear(embed_dim, num_kv_heads * self.head_dim, bias=bias)
        self.out_proj = nn.Linear(num_heads * self.head_dim, embed_dim, bias=bias)

        self.rotary_emb = RotaryEmbedding(
            head_dim=self.head_dim,
            max_seq_len=max_seq_len,
            theta=rope_theta,
        )

    def forward(
        self,
        x: torch.Tensor,                        # [b, seq_len, embed_dim]
        past_key_value: tuple[torch.Tensor, torch.Tensor] | None = None,
        position_ids: torch.Tensor | None = None,
        attn_mask: torch.Tensor | None = None,
        is_causal: bool = True,
        return_weights: bool = False,
    ):
        b, s, _ = x.shape

        q = self.q_proj(x).view(b, s, self.num_heads, self.head_dim)
        k = self.k_proj(x).view(b, s, self.num_kv_heads, self.head_dim)
        v = self.v_proj(x).view(b, s, self.num_kv_heads, self.head_dim)

        # Apply RoPE (to Q and K only)
        q = self.rotary_emb(q, seq_len=s, position_ids=position_ids)
        k = self.rotary_emb(k, seq_len=s, position_ids=position_ids)

        # KV cache append
        if past_key_value is not None:
            past_k, past_v = past_key_value
            k = torch.cat([past_k, k], dim=1)
            v = torch.cat([past_v, v], dim=1)
            new_past_key_value = (k, v)
        else:
            new_past_key_value = (k, v)

        # Transpose to SDPA format: [b, heads, seq, head_dim]
        q = q.transpose(1, 2)
        k = k.transpose(1, 2)
        v = v.transpose(1, 2)

        # Use Flash Attention backend (when possible)
        with sdpa_kernel(SDPBackend.FLASH_ATTENTION):
            # enable_gqa=True handles the grouping/broadcast internally
            out = F.scaled_dot_product_attention(
                q,
                k,
                v,
                attn_mask=attn_mask,
                dropout_p=self.dropout_p if self.training else 0.0,
                is_causal=is_causal,
                enable_gqa=True,           # <-- core for GQA
            )

        # Back to [b, s, embed_dim]
        out = out.transpose(1, 2).contiguous().view(b, s, -1)
        out = self.out_proj(out)

        if return_weights:
            # If you need weights, fallback to math backend (not fused)
            with sdpa_kernel(SDPBackend.MATH):
                _, weights = F.scaled_dot_product_attention(
                    q, k, v, is_causal=is_causal, enable_gqa=True, need_weights=True
                )
            return out, new_past_key_value, weights

        return out, new_past_key_value


# ────────────────────────────────────────────────────────────────
#   Quick test
# ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    device = "cuda" if torch.cuda.is_available() else "cpu"
    torch.manual_seed(0)

    model = GroupedQueryAttentionFlash(
        embed_dim=512,
        num_heads=8,
        num_kv_heads=2,          # GQA: 4 queries share each KV head
        rope_theta=500000.0,
    ).to(device)

    # Prefill example
    x = torch.randn(2, 64, 512, device=device)
    pos_ids = torch.arange(64, device=device).expand(2, 64)
    out, past_kv = model(x, position_ids=pos_ids, is_causal=True)
    print("Prefill out:", out.shape)           # [2, 64, 512]
    print("Cache len:", past_kv[0].shape[1])   # 64

    # Decode one token
    x_new = torch.randn(2, 1, 512, device=device)
    pos_new = torch.tensor([[64]], device=device)
    out_new, past_kv = model(
        x_new,
        past_key_value=past_kv,
        position_ids=pos_new,
        is_causal=True,
    )
    print("Decode out:", out_new.shape)        # [2, 1, 512]
    print("Updated cache:", past_kv[0].shape[1])  # 65