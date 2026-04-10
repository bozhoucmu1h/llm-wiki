---
type: concept
created: 2026-04-10
updated: 2026-04-10
tags: [architecture, efficient, MoE]
---

# Mixture of Experts

## Definition

MoE — 一种模型架构，将不同的"专家"子网络通过门控机制组合，实现大模型的能力但只激活部分参数。

## Key Aspects

- 降低推理成本（每次只激活部分专家）
- 代表应用：Mixtral 8x7B、GPT-4（据传）
- [[DeepSeek]]是MoE架构的积极创新者

## Related Concepts

- [[Transformer]] (inferred)
- [[Mistral]] (inferred)
- [[大语言模型]] (inferred)

## Sources

- [[大语言模型前沿]]
