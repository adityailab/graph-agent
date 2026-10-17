"""What the demo sessions are asked. The headless scenario is short; ShopLite is the live one."""

from __future__ import annotations

TOOLS = (
    "mcp__handoff__handoff",
    "mcp__handoff__why",
    "mcp__handoff__sessions",
    "mcp__handoff__record_decision",
    "mcp__handoff__record_need",
    "mcp__handoff__resolve_need",
    "mcp__handoff__send_message",
    "mcp__handoff__ask",
    "mcp__handoff__search",
)

HEADLESS: tuple[tuple[str, str], ...] = (
    (
        "frontend",
        "Create Checkout.tsx that shows the order total from order.totalPaise as rupees with two "
        "decimals. Record a decision: money stays in integer paise end to end, because "
        "floating-point rupees round wrongly. Record a need for the backend: the orders API must "
        "return totalPaise as an integer. Reply done.",
    ),
    (
        "backend",
        "Use the handoff tool to see what the frontend needs from you. Create api/orders.py with "
        "a function order_summary(order) that returns a dict whose totalPaise is an integer. "
        "Record a decision about it, resolve the frontend's need, then send the frontend a "
        "message that totalPaise is now returned by order_summary. Reply done.",
    ),
    ("frontend", "Carry on: is there any news from the other sessions? Reply in one line."),
    (
        "deploy",
        "Before deploying: use the handoff tool, and use the ask tool to ask the frontend role "
        "why amounts are kept in paise. Then tell me in three lines what the other sessions "
        "changed, why, and whether anything is still open.",
    ),
)

_INTRO = (
    "New project: ShopLite, a small online shop with a React frontend in web/ and a Python "
    "API in api/. "
)
_SHORT = " Keep files small and replies short."

# Rounds for the live grid: roles in one round work in parallel.
SHOPLITE: tuple[dict[str, str], ...] = (
    {
        "frontend": _INTRO + "You are the frontend. Create web/src/ProductList.tsx, "
        "web/src/ProductCard.tsx and web/src/cart/CartContext.tsx. Use the handoff tools to "
        "record your decisions (cart state lives in a React context; prices stay integer paise) "
        "and record a need for the backend: GET /api/products returning id, name, pricePaise and "
        "imageUrl." + _SHORT,
        "backend": _INTRO + "You are the backend. Create api/catalogue.py (an in-memory product "
        "list with integer pricePaise) and api/app.py with a GET /api/products route using "
        "FastAPI. Use the handoff tools to record your decisions." + _SHORT,
        "deploy": _INTRO + "You are deploy. Create deploy/api.Dockerfile, deploy/web.Dockerfile "
        "and docker-compose.yml (api on port 8000, web on 3000). Use the handoff tools to record "
        "your decisions, and record needs: from the backend a GET /health endpoint, from the "
        "frontend a build command that writes static files to web/dist." + _SHORT,
    },
    {
        "backend": "Check the handoff and your messages, then meet what the frontend and deploy "
        "need from you (including GET /health). Add api/orders.py with POST /api/orders that "
        "stores an order with an integer totalPaise. Record your decisions, resolve the needs you "
        "met, and send the frontend a message about the orders API." + _SHORT,
        "frontend": "Check the handoff and meet deploy's need for a build command "
        "(web/package.json with a build script writing web/dist). Then create "
        "web/src/Checkout.tsx that posts the cart to /api/orders, and web/src/Login.tsx. Decide "
        "where the auth token lives (an httpOnly cookie, never localStorage), record that "
        "decision, and record a need for the backend: POST /api/login that sets that cookie."
        + _SHORT,
    },
    {
        "backend": "Check the handoff for open needs. Add api/auth.py with POST /api/login "
        "issuing a JWT in an httpOnly cookie, signed with JWT_SECRET from the environment, and add "
        "a JWT_SECRET placeholder to the api service in docker-compose.yml. Record the decision, "
        "resolve the frontend's need, and send deploy a message that JWT_SECRET must be set as a "
        "secret." + _SHORT,
        "deploy": "Check the handoff and your messages. Add .github/workflows/ci.yml that runs the "
        "api tests and builds web. Use the ask tool to ask the backend what GET /health returns "
        "when the catalogue is empty. Record your decisions." + _SHORT,
    },
    {
        "deploy": "Check your messages, then make docker-compose.yml read JWT_SECRET from an env "
        "file instead of a placeholder. Then use the search tool for 'how do users stay signed "
        "in' and the handoff tool, and write a five-line release checklist: what each session "
        "built, why, and what is still open." + _SHORT,
        "frontend": "Use the why tool on docker-compose.yml and on api/auth.py, and tell me in two "
        "lines why they changed." + _SHORT,
    },
)
