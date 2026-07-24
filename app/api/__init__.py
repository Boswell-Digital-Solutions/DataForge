"""DataForge API package.

Routers are imported explicitly by ``app.main``. Keeping this initializer free
of eager imports prevents retired AuthorForge content routers from being loaded
as an accidental side effect of importing an unrelated API module.
"""
