from fastapi import FastAPI, Form, Request, UploadFile, File
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi import Cookie
from itsdangerous import URLSafeSerializer
import pandas as pd
import shutil
import json
import os

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/assets", StaticFiles(directory="assets"), name="assets")
templates = Jinja2Templates(directory='templates')
serializer = URLSafeSerializer('your-secret-key')


@app.middleware("http")
async def session_middleware(request: Request, call_next):
    # Đọc session từ cookie nếu có
    session_data = request.cookies.get("session")
    if session_data:
        try:
            # Giải mã session data
            request.state.session = json.loads(serializer.loads(session_data))
        except:
            request.state.session = {}
    else:
        request.state.session = {}

    # Xử lý request
    response = await call_next(request)

    # Lưu session vào cookie
    if hasattr(request.state, "session"):
        session_data = serializer.dumps(json.dumps(request.state.session))
        response.set_cookie("session", session_data)

    return response


@app.get("/login")
async def login(request: Request):
    # Hiển thị form đăng nhập
    return templates.TemplateResponse('login.html', {"request": request})


@app.post("/login")
async def check_login(request: Request, username: str = Form(...), password: str = Form(...)):
    # Xác thực người dùng
    df = pd.read_csv('account/user_account.csv')
    data = {row['account']: row['password'] for _, row in df.iterrows()}
    if str(data[username]) == str(password):
        request.state.session["username"] = username
        return RedirectResponse('/', status_code=303)
    else:
        return RedirectResponse('/login', status_code=303)


@app.post('/logout')
async def logout(request: Request, response: RedirectResponse):
    response.delete_cookie("session_token")
    return RedirectResponse('/login', status_code=303)


@app.get("/")
async def get_folder(request: Request):
    # Hiển thị trang chủ
    user_name = request.state.session["username"]
    root_directory = f"data/{user_name}"
    folders = [f for f in os.listdir(root_directory)]
    return templates.TemplateResponse('home.html', {"request": request,
                                                    "user_name": user_name,
                                                    "folders": folders})


@app.post("/folder")
async def create_folder(request: Request, folder: str = Form(...)):
    user_name = request.state.session["username"]
    # Tạo thư mục mới
    directory = f"data/{user_name}/{folder}"
    os.makedirs(directory, exist_ok=True)
    return RedirectResponse('/', status_code=303)

# @app.put("/folder")
# async def rename_folder(request: Request, folder: str = Form(...)):
#     user_name = request.state.session["username"]
#     # Tạo thư mục mới
#     directory = f"data/{user_name}/{folder}"
#     os.makedirs(directory, exist_ok=True)
#     return RedirectResponse('/folder', status_code=303)

# @app.delete("/folder")
# async def delete_folder(request: Request, fol: str):
#     user_name = request.state.session["username"]
#     directory = f"data/{user_name}/{fol}"
#     os.removedirs(directory)
#     return RedirectResponse('/folder', status_code=303)


@app.get("/folder/{folder}")
async def get_file(request: Request, folder: str):
    user_name = request.state.session["username"]
    root_directory = f"data/{user_name}/{folder}"
    items = [f for f in os.listdir(root_directory)]
    return templates.TemplateResponse('folder.html', {"request": request,
                                                      "user_name": user_name,
                                                      "folders": items})


@app.post("/folder/{folder}")
async def upload_file(request: Request, folder: str, file: UploadFile = File(...)):
    try:
        user_name = request.state.session['username']
        file_location = f"data/{user_name}/{folder}/{file.filename}"
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return RedirectResponse(f'/folder/{folder}', status_code=303)

    except Exception as e:
        return JSONResponse(content={"message": f"Error: {str(e)}"}, status_code=500)
