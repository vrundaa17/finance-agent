from fastapi import APIRouter, HTTPException
import api.db_repo.report_db as watchlist
import api.schema as schema
import utils
app= APIRouter(tags=['Watchlist'])


@app.get("/watchlists")
def get_all_watchlists():
    """List all the watchlists"""
    return watchlist.list_watchlist()
 
@app.post("/watchlists")
def create_new_watchlist(request: schema.Watchlist):
    """Create new watchlist"""
    result=  watchlist.create_watchlist(request.name)
    if result.get("status")=="exists":
        raise HTTPException(status_code=400,detail=f"Watchlist {request.name} already exists.")
    return result


@app.get("/watchlists/{watchlist_name}")
def get_stock_watchlist(watchlist_name: str):
    """ Get all the stock in a watchlist"""
    stock_name = watchlist.get_stock(watchlist_name)
    if stock_name is None:
        raise HTTPException(status_code=404, detail=f"Watchlist '{watchlist_name}' not found")
    return {"watchlist": watchlist_name, "stock_name": stock_name}

@app.post("/watchlists/add")
def add_to_watchlist(body: schema.StockAdd):
    stock_name = utils._normalise_stock(body.stock_name)
    result = watchlist.add_stock(body.watchlist_name, stock_name, body.notes or None)
    if result.get("status") == "invalid":
        raise HTTPException(status_code=429, detail=result["message"])
    if result.get("status") == "error":
        raise HTTPException(status_code=404, detail=result["message"])
    if result.get("status") == "exists":
        raise HTTPException(status_code=400, detail=f"'{body.stock_name}' is already in '{body.watchlist_name}'")
    return result


@app.delete("/watchlists/{watchlist_name}/{stock}")
def remove_stock(watchlist_name:str,stock:str):
    """Remove from the watchlist"""
    result=  watchlist.remove_stock(watchlist_name,stock)
    if result.get("status") == "not found":
        raise HTTPException(status_code=404, detail=f"'{stock}' not found in '{watchlist_name}'")
    return result

@app.delete("/watchlists/{watchlist_name}")
def delete_existing_watchlist(watchlist_name: str):
    """Delete the watchlist"""
    result =  watchlist.delete_watchlist(watchlist_name)
    if result.get("status") == "error":
        raise HTTPException(status_code=404, detail=result["message"])
    return result


