from starlette.responses import RedirectResponse
from fastapi import Request, HTTPException
from fastapi import FastAPI, Form, Request, UploadFile, File, Body
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi import Cookie
from itsdangerous import URLSafeSerializer
from model.model import *
import re
import pandas as pd
import shutil
import json
import os
from utils.common import *

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
async def check_login(request: Request, user: LoginModel):
    # Xác thực người dùng
    df = pd.read_csv('account/user_account.csv')
    data = {row['account']: row['password'] for _, row in df.iterrows()}
    if user.username not in data.keys():
        return JSONResponse({"message":"username was not exists"}, status_code=404)
    if str(data[user.username]) != str(user.password):
        return JSONResponse({"message":"Wrong"}, status_code=400)
    else:
        request.state.session['username'] = user.username
        return JSONResponse({"message":"Successfully login"}, status_code=200)


@app.post('/logout')
async def logout(request: Request, response: RedirectResponse):
    request.state.session.clear()
    response.delete_cookie("session_token")
    return RedirectResponse('/login', status_code=303)


@app.get("/")
async def get_folder(request: Request):
    # Hiển thị trang chủ
    user_name = request.state.session.get('username')
    if user_name:
        folders = [f for f in os.listdir(f"data/{user_name}")]
        return templates.TemplateResponse('home.html', {"request": request,
                                                        "user_name": user_name,
                                                        "folders": folders})
    else:
        return RedirectResponse('/login', status_code=303)


@app.post("/folder")
async def create_folder(request: Request, model: CreateModel):
    user_name = request.state.session.get("username")
    directory = f"data/{user_name}/{model.name}"
    if not user_name:
        raise HTTPException(
            status_code=401, detail="Unauthorized: Please login first")
    if contains_special_characters(model.name) or model.name == '':
        return JSONResponse({"message": f"Folder name {model.name} invalid"}, status_code=400)
    if os.path.exists(directory):
        return JSONResponse({"message": f"{model.name} already exists"}, status_code=409)
    try:
        os.makedirs(directory)
        return JSONResponse({"message": f"{model.name} was created"}, status_code=200)
    except OSError:
        return JSONResponse({"message": f"{model.name} has special symbol"}, status_code=400)


@app.put("/folder")
async def rename_folder(request: Request, folder: RenameModel):
    user_name = request.state.session.get("username")
    old = f"data/{user_name}/{folder.old_name}"
    new = f"data/{user_name}/{folder.new_name}"

    if not user_name:
        raise HTTPException(status_code=401, detail="Unauthorized: Please login first")
    if contains_special_characters(folder.new_name):
        return JSONResponse({'message': 'New folder name contains special symbols, which are not allowed.'}, status_code=400)
    if not os.path.exists(old):
        return JSONResponse({'message': f'{folder.old_name} was not exists'}, status_code=404)
    if folder.old_name == folder.new_name:
        return JSONResponse({'message': 'You must change folder name'}, status_code=400)
    try:
        os.rename(old, new)
        return JSONResponse({'message': f'Successfully renamed folder.'}, status_code=200)
    except OSError:
        return JSONResponse({'message': 'Failed to rename folder due to a system error or invalid folder name.'}, status_code=400)


@app.delete("/folder")
async def delete_folder(request: Request, folder: DeleteModel):
    user_name = request.state.session.get("username")
    directory = f"data/{user_name}/{folder.name}"
    
    if not user_name:
        raise HTTPException(status_code=401, detail="Unauthorized: Please login first")
    
    if not os.path.exists(directory):
        return JSONResponse({'message': f'{folder.name} was not exists'}, status_code=404)

    if os.listdir(directory) == []:
        os.removedirs(directory)
        return JSONResponse({'message': f'Successfully deleted folder'}, status_code=200)
    
    else:
        return JSONResponse({'message': f'Folder was not empty'}, status_code=400)


@app.get("/folder/{folder}")
async def get_file(request: Request, folder: str):
    user_name = request.state.session.get("username")
    directory = f"data/{user_name}/{folder}"
    
    if not user_name:
        raise HTTPException(status_code=401, detail="Unauthorized: Please login first")
    
    if not os.path.exists(directory):
        return JSONResponse({'message': f'{folder} was not exists'}, status_code=404)
    
    images = [f for f in os.listdir(directory)]
    return templates.TemplateResponse('folder.html', {"request": request,
                                                      "user_name": user_name,
                                                      "folders": images})


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


@app.put("/folder/{folder}")
async def rename_file(request: Request, file: RenameFileModel):
    user_name = request.state.session.get("username")
    old = f"data/{user_name}/{file.folder}/{file.old_name}"
    new = f"data/{user_name}/{file.folder}/{file.new_name}"
    
    if not user_name:
        raise HTTPException(status_code=401, detail="Unauthorized: Please login first")
    
    # if contains_special_characters(file.new_name):
    #     return JSONResponse({'message': 'New file name contains special symbols, which are not allowed.'}, status_code=400)
    
    if not os.path.exists(old):
        return JSONResponse({'message': f'{file.old_name} was not exists'}, status_code=404)
    
    if file.old_name == file.new_name:
        return JSONResponse({'message': 'You must change file name'}, status_code=400)
    
    try:
        os.rename(old, new)
        return JSONResponse({'message': f'Successfully renamed file.'}, status_code=200)
    
    except OSError:
        return JSONResponse({'message': 'Failed to rename file due to a system error or invalid file name.'}, status_code=400)
    

@app.delete("/folder/{folder}")
async def delete_file(request: Request, file: DeleteFileModel):
    user_name = request.state.session.get("username")
    file_path = f"data/{user_name}/{file.folder}/{file.name}"
    
    if not user_name:
        raise HTTPException(status_code=401, detail="Unauthorized: Please login first")
    
    if os.path.exists(file_path):
        os.remove(file_path)
        return JSONResponse({"message": "Successfully deleted file"}, status_code=200)
    else:
        return JSONResponse({"message": "File not exists"}, status_code=404)
