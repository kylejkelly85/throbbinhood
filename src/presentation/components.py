from fasthtml.common import Html, Head, Title, Script, Body, Div, Header, H1, Tr, Td, A, Button, Table, Thead, Th, Tbody
from typing import Any
from src.domain.entities import Asset

def Layout(title: str, *content: Any) -> Html:
    return Html(
        Head(
            Title(title),
            Script(src="https://unpkg.com/htmx.org@1.9.12"),
            Script(src="https://cdn.tailwindcss.com")
        ),
        Body(
            Div(
                Header(
                    H1(title, cls="text-3xl font-bold text-gray-900"),
                    cls="mb-8"
                ),
                *content,
                cls="max-w-7xl mx-auto p-4"
            )
        )
    )

def AssetTable(assets: list[Asset], page: int) -> Div:
    rows = []
    for asset in assets:
        if not asset.is_downloaded:
            action_td = Td(
                Button(
                    "Download",
                    hx_post=f"/download/{asset.id}",
                    hx_target="closest tr",
                    hx_swap="outerHTML",
                    cls="bg-green-500 text-white px-2 py-1 rounded"
                ),
                cls="p-2 border"
            )
        else:
            action_td = Td("Ingested ✓", cls="p-2 border text-green-600 font-bold")

        rows.append(Tr(
            Td(asset.title or "", cls="p-2 border"),
            Td(A(asset.url or "", href=asset.url or "#", target="_blank", cls="text-blue-500"), cls="p-2 border"),
            Td(f"{asset.confidence_score:.2f}" if asset.confidence_score is not None else "0.00", cls="p-2 border"),
            action_td
        ))

    pagination = []
    if page > 1:
        pagination.append(A("Previous", href=f"/?page={page-1}", cls="text-blue-500 mr-4"))
    if len(assets) == 50:
        pagination.append(A("Next", href=f"/?page={page+1}", cls="text-blue-500"))

    pagination_div = Div(*pagination, cls="mt-4") if pagination else None

    return Div(
        Table(
            Thead(Tr(
                Th("Title", cls="p-2 border"),
                Th("URL", cls="p-2 border"),
                Th("Score", cls="p-2 border"),
                Th("Status/Action", cls="p-2 border")
            )),
            Tbody(*rows),
            cls="w-full text-sm text-left rtl:text-right text-gray-500"
        ),
        *([pagination_div] if pagination_div else []),
        id="asset-table",
        cls="relative overflow-x-auto"
    )