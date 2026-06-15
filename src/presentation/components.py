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
        rows.append(Tr(
            Td(asset.title, cls="p-2 border"),
            Td(A(asset.url, href=asset.url, target="_blank", cls="text-blue-500"), cls="p-2 border"),
            Td(f"{asset.confidence_score:.2f}", cls="p-2 border"),
            Td(Button("Download", cls="bg-green-500 text-white px-2 py-1 rounded"), cls="p-2 border")
        ))
    
    return Div(
        Table(
            Thead(Tr(Th("Title", cls="p-2 border"), Th("URL", cls="p-2 border"), Th("Score", cls="p-2 border"), Th("Action", cls="p-2 border"))),
            Tbody(*rows),
            cls="w-full border-collapse"
        ),
        Div(
            A("Previous", href=f"/?page={page-1}", cls="text-blue-500 mr-4") if page > 1 else "",
            A("Next", href=f"/?page={page+1}", cls="text-blue-500") if len(assets) == 50 else "",
            cls="mt-4"
        ),
        id="asset-table"
    )
