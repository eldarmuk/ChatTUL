# Lodz University of Technology Admissions Chatbot

## How to update the knowledge base
- All official data is stored in `datasources.json` (retrieved: 2025-06-16).
- To update, visit the official TUL admissions and programme pages, update the JSON, and retrain the model.
- If new fields of study or rules are added, update both `datasources.json` and the NLU/domain files as needed.

## How to retrain
1. Run `rasa train` in the project directory.
2. To test, run `rasa test`.

## How to add new programmes
- Add the new programme to `datasources.json` under `field_of_study`.
- Add NLU examples for the new field in `nlu.yml`.
- Add response templates or update the custom action if needed.

## Source URLs
- All URLs and summaries are from official TUL pages as of 2025-06-16. See `datasources.json` for details.

## Maintenance
- Schedule periodic review of official TUL pages.
- Update `datasources.json` and retrain as needed.
- Version-control all files.
