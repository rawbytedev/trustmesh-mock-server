"""
Docstring for feedback_server
This is the server used by the AI it provides feedback regarding shipments status
in real use case the shipment provider sets it up to allow Ai to perform queries
"""
import os
from fastapi import FastAPI,Request, Form
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Dict, List, Union
import datetime
import logging

import uvicorn


app = FastAPI(title="TrustMesh Feedback Server")
# Configure logging
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
states = ["PENDING","IN-TRANSIT","DELIVERED", "ANOMALY", "DELAY"]
memory:Dict[str, int]={}

# In-memory store for shipments
shipments: Dict[str, Dict] = {} ## dictionary are mutable
app.state.debugmode = True ## bool are not so we use app.state
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
single_delay = 0
class QueryRequest(BaseModel):
    """This is the Model used to query for shipments"""
    ids: Union[List[str], str] # list
class State(BaseModel):
    pass
class ResponseModel(BaseModel):
    """This is the Model used by server to respond to queries"""
    details: List[Dict[str, str]]

# Error handling
"""
We handle errors manually to avoid leaking details to frontend or API users
"""
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=400,
        content={"error": "Invalid request format or parameters."},
    )

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    # Override default HTTP errors too
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail if exc.detail else "An error occurred."},
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    # Log the real error internally
    logging.error(f"Unexpected error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error. Please try again later."},
    )

# Peform a single query and reply with shipment details in json
@app.post("/query")
async def query_shipments(req: QueryRequest) -> ResponseModel:
    """API endpoint to get shipment details, support both single input or list
    All requests must follow the format `{"ids":"item"}` or `{"ids":["item1","item2"]}`
    """
    logging.info(f"query request was made: {req}")
    ids = req.ids
    logging.info("Retrieving details from storage")
    if isinstance(ids, str):
        details = [get_shipment_detail(ids)]
    else:
        details = [get_shipment_detail(i) for i in ids]
    return ResponseModel(details=details)

# helper function: retrieve shipments from storage
def get_shipment_detail(ship_id:str)-> dict[str, str]:
    """Retrieve shipment from storage"""
    if ship_id.__contains__("-n-"):
        return demo_normalflow(ship_id)
    if ship_id.__contains__("-xr-"): ## shipment doesn't exist so it expires
        return {"id":ship_id, "status":"Unknown", "notes":"not available", "location":"Unknown", "timestamp":timestamp()}
    if ship_id in shipments:
        return {"id":ship_id, **shipments[ship_id]}
    else:
        if app.state.debugmode:
            shipments[ship_id] = {"id":ship_id, "status":"Debug", "location":"LocalHost","notes":"Debug", "timestamp":timestamp()} 
            return shipments[ship_id]
        return {"id":ship_id, "status":"Unknown", "notes":"not available", "location":"Unknown", "timestamp":timestamp()}

## entry point of App
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    """Entry point of App"""
    context = {"request": request, "shipments": shipments, "debug": app.state.debugmode}
    return templates.TemplateResponse("index.html", context=context)

## Add shipment details from dashboard
@app.post("/add", response_class=HTMLResponse)
def add_shipment(request: Request, id:str =Form(...), status:str=Form(...),location:str =Form(...),notes:str=Form("")):
    """Add shipment to storage"""
    logging.info("Adding shipments to storage")
    shipments[id]= {"status":status, "location":location, "notes":notes, "timestamp":timestamp()} 
    logging.info("Shipment added successfully")
    return redirect()

## toggle debug mode (autoadd)
@app.post("/toggle_autoadd", response_class=HTMLResponse)
def toggle(request: Request):
    """toggle auto-add option"""
    if app.state.debugmode:
        app.state.debugmode = False
        logging.info("Debug mode disabled")
        return redirect()
    app.state.debugmode = True
    logging.info("Debug mode enabled")
    return redirect()

## return the status of server
@app.get("/health")
def health():
    """Check the health status of Server"""
    return {"status": "ok", "shipments_tracked": len(shipments)}

## give current timestamp 
def timestamp():
    """A helper to generate timestamp"""
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

## redirect to home page
def redirect():
    """handle redirections to `/` path; a safe guard against sending same request on reload"""
    return RedirectResponse(url="/", status_code=303)

def demo_normalflow(ship_id:str)-> dict[str, str]:
    """Hnadle request relate to demo"""
    global single_delay
    if ship_id in shipments:
        ## stop last state
        if memory[ship_id] == 2:
            ## trigger a delay
            if single_delay == 0:
                memory[ship_id] = memory[ship_id]-1
                location = shipments[ship_id]['location']
                notes= shipments[ship_id]['notes']
                shipments[ship_id] ={"status":states[-1], "location":location, "notes":notes, "timestamp":timestamp()}
                single_delay = 1
                return {"id":ship_id, **shipments[ship_id]}
        if memory[ship_id] == 2:
            return {"id":ship_id, **shipments[ship_id]}
        memory[ship_id] = memory[ship_id]+1
        location = shipments[ship_id]['location']
        notes= shipments[ship_id]['notes']
        shipments[ship_id] = {"status":states[memory[ship_id]], "location":location, "notes":notes, "timestamp":timestamp()}
    else:
        memory[ship_id] = 0
        shipments[ship_id] = {"status":states[memory[ship_id]], "location":"NYC", "notes":"notes", "timestamp":timestamp()}
    return {"id":ship_id, **shipments[ship_id]}

def start_server():
    """Starts the server"""
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
    
@app.get("/clear")
def clear():
    """Clear all shipments from storage"""
    shipments.clear()
    logging.info("Cleared all shipments from storage")
    return redirect()

if __name__ == "__main__":
    start_server()