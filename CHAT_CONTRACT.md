# AI Chat contract (not implemented)

The AI provider is not chosen yet. Do **not** call these endpoints — they are not built.

When they ship, the app's chat service should match this contract.

## POST /api/v1/chat/conversations

Start a chat.

```json
{
  "persona": "cardiologist",
  "concern_id": "chest-pain",
  "health_tip_id": null
}
```

- `persona` is `general` (AI Health Assistant) or a category slug (AI [Category]).
- `concern_id` or `health_tip_id` is set when the chat starts from Concern Detail or Health Tip Detail.
- Response includes conversation `id`, display title, and the opening greeting as the first AI message.

## POST /api/v1/chat/conversations/{id}/messages

Send a message and stream the AI reply with Server-Sent Events.

```json
{
  "client_message_id": "7f3c9a2e-0000-4000-8000-000000000000",
  "text": "When should I worry about chest pain?"
}
```

- `client_message_id` is a UUID from the app. A resend with the same id must not create a second message or reply.
- Add the user's health profile (age, gender, height, weight, blood group, allergies, conditions) to the AI context.
- The AI gives guidance, not diagnoses, and tells users to call emergency services for emergency symptoms.

## GET /api/v1/chat/conversations/{id}/messages

Load an existing chat, oldest first, paginated with a cursor.
