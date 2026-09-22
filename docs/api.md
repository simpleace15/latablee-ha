# LaTablée API — connector cheat sheet

Endpoints the HA connector uses. Auth: `Authorization: Bearer <device token>`
(create in LaTablée → Settings → Device tokens).

| Purpose | Endpoint |
|---|---|
| Verify token / user | `GET /api/v1/auth/me` |
| Shopping lists | `GET /api/v1/lists` |
| List detail (items) | `GET /api/v1/lists/{id}` |
| Add item | `POST /api/v1/lists/{id}/items` — `{"name":"milk","quantity":2,"unit":"cups"}` |
| Check/uncheck | `PATCH /api/v1/lists/{id}/items/{item_id}` — `{"done":true}` |
| Delete item | `DELETE /api/v1/lists/{id}/items/{item_id}` |
| Weekly plan | `GET /api/v1/plan?days=7` |
| Add plan entry | `POST /api/v1/plan` — `{"date":"2026-09-22","slot":"dinner","title_override":"tacos"}` |
| Recipes search | `GET /api/v1/recipes?q=chicken` |
| Freeform NLU | `POST /api/v1/voice/command` — `{"transcript":"refill my week"}` |
| Events (poll) | `GET /api/v1/events?after_id=0` |

## curl examples

```bash
BASE=https://latablee.example.com
TOK="lat_your_device_token"

# who am I
curl -fsS -H "Authorization: Bearer $TOK" $BASE/api/v1/auth/me

# add milk to the first shopping list
LID=$(curl -fsS -H "Authorization: Bearer $TOK" $BASE/api/v1/lists | jq '.[0].id')
curl -fsS -X POST -H "Authorization: Bearer $TOK" -H "Content-Type: application/json" \
  -d '{"name":"milk","quantity":1,"unit":"gallon"}' $BASE/api/v1/lists/$LID/items

# plan tacos for dinner on a date
curl -fsS -X POST -H "Authorization: Bearer $TOK" -H "Content-Type: application/json" \
  -d '{"date":"2026-09-22","slot":"dinner","title_override":"tacos"}' $BASE/api/v1/plan

# what is for dinner tonight (via NLU - works freeform)
curl -fsS -X POST -H "Authorization: Bearer $TOK" -H "Content-Type: application/json" \
  -d '{"transcript":"what is for dinner tonight"}' $BASE/api/v1/voice/command

# poll events since id
curl -fsS -H "Authorization: Bearer $TOK" "$BASE/api/v1/events?after_id=0&limit=50"
```

## Voice command responses

`{"reply": "Tacos is on the menu for tonight.", "actions": [{...structured action...}]}`

`reply` is TTS-ready; `actions` lists what was applied (plan_entry, list_item, refill_week...).
