from fastapi import APIRouter, HTTPException
import api.watchlist as watchlist
import api.schema as schema

app= APIRouter(tags=['Watchlist'])


@app.get("/watchlists")
def get_all_watchlists():
    """List all the watchlists"""
    return watchlist.list_watchlist()
 
@app.post("/watchlists")
def create_new_watchlist(request: schema.Watchlist):
    """Create new watchlist"""
    return watchlist.create_watchlist(request.name)

@app.get("/watchlists/{watchlist_name}")
def get_stock_watchlist(watchlist_name: str):
    """ Get all the stock in a watchlist"""
    stock_name = watchlist.get_stock(watchlist_name)
    if stock_name is None:
        raise HTTPException(status_code=404, detail=f"Watchlist '{watchlist_name}' not found")
    return {"watchlist": watchlist_name, "stock_name": stock_name}

@app.post("/watchlists/add")
def add_to_watchlist(body:schema.StockAdd):
    """Add stocks to the watchlist"""
    return watchlist.add_stock(body.watchlist_name,body.stock_name,body.notes or None)

@app.delete("/watchlists/{watchlist_name}/{stock}")
def remove_stock(watchlist_name:str,stock:str):
    """Remove from the watchlist"""
    return watchlist.remove_stock(watchlist_name,stock)

@app.delete("/watchlists/{watchlist_name}")
def delete_existing_watchlist(watchlist_name: str):
    """Delete the watchlist"""
    return watchlist.delete_watchlist(watchlist_name)


