# Anthropic Streaming API Rule

When implementing any Claude API streaming in this codebase, always follow these patterns.

---

## Model to Use

Always use: `claude-sonnet-4-20250514`
Max tokens: 1500 for thesis cards, 2500 for deep research, 800 for quick summaries.

## Async Streaming Pattern (Backend)

```python
import anthropic

client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

async with client.messages.stream(
    model="claude-sonnet-4-20250514",
    max_tokens=1500,
    system=SYSTEM_PROMPT,
    messages=[{"role": "user", "content": user_content}],
) as stream:
    async for chunk in stream.text_stream:
        yield f"data: {json.dumps({'token': chunk})}\n\n"

yield "data: [DONE]\n\n"
```

## SSE FastAPI Response

```python
return StreamingResponse(
    event_generator(),
    media_type="text/event-stream",
    headers={
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
        "Access-Control-Allow-Origin": "*",    # required for localhost dev
    },
)
```

## SSE Frontend Pattern

```typescript
// Always use EventSource, never fetch() for SSE
const es = new EventSource(`/api/arb/${id}/thesis`);
es.onmessage = (e) => {
  if (e.data === "[DONE]") { es.close(); return; }
  const { token } = JSON.parse(e.data);
  setText(prev => prev + token);
};
es.onerror = () => es.close();
```

## Component Rule

Any React component that uses EventSource MUST have `"use client"` at the top.
EventSource is browser-only. SSR will break without this directive.

## Never

- Never use sync `anthropic.Anthropic()` for streaming endpoints — use `AsyncAnthropic`
- Never use `fetch()` for consuming SSE in the browser — use `EventSource`
- Never leave an EventSource open after the component unmounts — always close in cleanup
