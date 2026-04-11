# Analyse tarifaire — Providers LLM
**Projet** : Wiki LLM
**Date** : 2026-04-11
**Contexte** : choix du provider LLM pour le module synthesizer.py

---

## Profil d'usage Wiki LLM

Une ingestion = ~10 000 tokens input / ~3 000 tokens output.
- Input : fiche source + pages concepts existantes + prompt système
- Output : JSON structuré (page source + mises à jour concepts + contradictions + compte-rendu)

---

## Tableau comparatif (avril 2026)

| Provider | Modèle | Input /M | Output /M | Batch -50% | Coût 25 fiches MVP | Coût 1 000 fiches V2 |
|---|---|---|---|---|---|---|
| **Gemini** | 2.5 Flash-Lite | $0,10 | $0,40 | ✅ | ~$0,02 | ~$0,35 |
| **Gemini** | 2.5 Flash | $0,30 | $2,50 | ✅ | ~$0,05 | ~$0,90 |
| **Claude** | Haiku 4.5 | $0,80 | $4,00 | ✅ | ~$0,03 | ~$0,80* |
| **Claude** | Sonnet 4.6 | $3,00 | $15,00 | ✅ | ~$0,19 | ~$7,50 |
| **Ollama** | Qwen 3.5 9B | $0 | $0 | — | $0 | $0 (mais ~25-33h machine) |

*avec prompt caching (90% réduction sur inputs répétés)

---

## Free tier

| Provider | Limite réelle | Utilisable pour MVP ? |
|---|---|---|
| Gemini API | ~20 req/jour (constaté sur YT Extractor) | ⚠️ 25 fiches = 2 sessions minimum |
| Claude API | Crédits starter ~$5 (non durable) | ⚠️ Test uniquement |
| Ollama local | Illimité | ✅ Zéro coût |

**Alerte** : Gemini 2.0 Flash-Lite déprécié — fermeture juin 2026. Migrer vers 2.5 Flash-Lite.

---

## Décision retenue (Décision 10)

### Workflow A — MVP, ingestion unitaire supervisée
**Provider** : Ollama + Qwen 3.5 9B (local)
- Coût : zéro
- Données : ne quittent pas la machine
- Performance : ~25-35 tok/s sur MBP M5 16 Go
- Limite : Ollama MLX (x2 vitesse) requiert 32 Go — non disponible sur ce hardware

### Workflow B — V2, batch Evernote ~1 000 fiches
**Provider** : Gemini 2.5 Flash-Lite en mode batch
- Coût : ~$0,35 pour 1 000 fiches
- Discount batch : 50% automatique en activant la facturation Google Cloud
- Pas d'abonnement requis — pay-as-you-go Tier 1

### Fallback qualité
**Provider** : Claude Haiku 4.5 avec prompt caching
- Coût : ~$0,80 pour 1 000 fiches (avec caching)
- Avantage : prompt caching 90% sur inputs répétés (prompt système identique à chaque ingestion)

---

## Configuration

```yaml
# Workflow A — local (défaut)
llm_provider: ollama
ollama_model: qwen3.5:9b
ollama_base_url: http://localhost:11434

# Workflow B — batch Gemini
# llm_provider: gemini
# gemini_model: gemini-2.5-flash-lite

# Fallback qualité — Claude
# llm_provider: claude
# claude_model: claude-haiku-4-5
```

Changement de provider = une ligne dans `config.yml`.
Couche abstraite `LLMProvider` héritée de YT Extractor.

---

## Hardware

**MBP M5 16 Go RAM — performances Ollama**

| Modèle | RAM requise | Vitesse | Verdict |
|---|---|---|---|
| Qwen 3.5 9B Q4 | ~7 Go | ~25-35 tok/s | ✅ recommandé |
| Qwen 3 8B Q4 | ~6 Go | ~30-40 tok/s | ✅ viable |
| Qwen 2.5 14B Q4 | ~11 Go | ~15-20 tok/s | ⚠️ serré |
| Qwen 3.5 27B Q4 | ~20 Go | — | ❌ ne rentre pas |

Note : Ollama MLX (double la vitesse sur M5) requiert 32 Go minimum.

---

*Produit dans le projet Claude.ai Wiki LLM — session du 2026-04-11*
