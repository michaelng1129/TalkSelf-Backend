import base64
import difflib
from glob import glob
import os
import re
import shutil
import subprocess
from unittest import result
import fastapi
import fastapi.security as security
from numpy import imag
import sqlalchemy
import sqlalchemy.orm as orm
import services, schemas 


app = fastapi.FastAPI()

@app.get("/download")
def download_file():
    file_path = os.path.join("LocalDB", "EngDB.json")
    return fastapi.responses.FileResponse(file_path)

@app.post("/api/usersCreate")
async def create_user(
    email: str = fastapi.Form(...), 
    name: str = fastapi.Form(...),
    password: str = fastapi.Form(...),
    image: str = fastapi.Form(...),
    db: sqlalchemy.orm.Session = fastapi.Depends(services.get_db)
):
    try:
        print(image)
        db_user = await services.get_user_by_email(email, db)
        if db_user:
            raise fastapi.HTTPException(status_code=400, detail="Email already in use")

        file_path = None
        if image:
            file_path = await services.save_uploaded_file(email, image)
            print("File path:", file_path)

        user = schemas.UserCreate(email=email, password=password)
        new_user = await services.create_user(user, db)


        user_info = schemas.UserInfoCreate(user_id=new_user.id, name=name, avatar_url = file_path)
        await services.create_user_info(user_info, db)
        
        return await services.create_token(new_user)

    except Exception as e:
            raise fastapi.HTTPException(status_code=500, detail=str(e))

@app.post("/api/token")
async def generate_token(
    form_data: security.OAuth2PasswordRequestForm = fastapi.Depends(),
    db: orm.Session = fastapi.Depends(services.get_db),
):
    user = await services.authenticate_user(form_data.username, form_data.password, db)
    
    if not user:
        raise fastapi.HTTPException(status_code=401, detail="Invalid Credentials")

    return await services.create_token(user)

@app.post("/api/ttsDictionary")
async def run_ttsDictionary(
    request: fastapi.Request,
    db: orm.Session = fastapi.Depends(services.get_db)
):
    data = await request.json()
    word = data.get("data", {}).get("word")
    jwt = data.get("data", {}).get("jwt")

    avatar = await services.get_user_avatar(db, jwt)
    audio = await services.get_audio(word)

    os.chdir(os.path.join(".", "faceGenerator"))

    avatar_folder = ".."
    avatar_path = os.path.join(avatar_folder, avatar)

    audio_folder = ".."
    audio_path = os.path.join(audio_folder, audio)

    python_executable = os.path.join("..","venv", "Scripts", "python.exe")

    inference = os.path.join(".", "inference.py")
    checkpoint = os.path.join(".", "checkpoints")
    result = os.path.join(".", "results")
    gfpgan = ("gfpgan")

    subprocess.run([python_executable, inference, "--driven_audio", audio_path, "--source_image", avatar_path, "--enhancer", gfpgan, "--checkpoint_dir", checkpoint,  "--result_dir", result])
    latest_result = max(glob(os.path.join(result, '*')), key=os.path.getctime)
    user = await services.get_current_user(db, jwt)
    new_filename = f"{user.id}.mp4"
    shutil.move(latest_result, os.path.join(result, new_filename))
    os.chdir(os.path.join(".."))

    video_path = os.path.join(".", "faceGenerator", "results", new_filename)
    with open(video_path, "rb") as video_file:
        video_data = video_file.read()
        video_base64 = base64.b64encode(video_data).decode("utf-8")
    return fastapi.responses.JSONResponse(content={"video_base64": video_base64})

@app.post("/api/ttsWriting")
async def run_ttsWriting(
    request: fastapi.Request,
    db: orm.Session = fastapi.Depends(services.get_db)
):
    data = await request.json()
    Text = data.get("data", {}).get("text")
    jwt = data.get("data", {}).get("jwt")

    avatar = await services.get_user_avatar(db, jwt)
    audio = await services.get_audio(Text)

    os.chdir(os.path.join(".", "faceGenerator"))

    avatar_folder = ".."
    avatar_path = os.path.join(avatar_folder, avatar)

    audio_folder = ".."
    audio_path = os.path.join(audio_folder, audio)

    python_executable = os.path.join("..","venv", "Scripts", "python.exe")

    inference = os.path.join(".", "inference.py")
    checkpoint = os.path.join(".", "checkpoints")
    result = os.path.join(".", "results")
    gfpgan = ("gfpgan")

    subprocess.run([python_executable, inference, "--driven_audio", audio_path, "--source_image", avatar_path, "--enhancer", gfpgan, "--checkpoint_dir", checkpoint,  "--result_dir", result])
    latest_result = max(glob(os.path.join(result, '*')), key=os.path.getctime)
    user = await services.get_current_user(db, jwt)
    new_filename = f"{user.id}_full.mp4"
    shutil.move(latest_result, os.path.join(result, new_filename))
    os.chdir(os.path.join(".."))

    video_path = os.path.join(".", "faceGenerator", "results", new_filename)
    with open(video_path, "rb") as video_file:
        video_data = video_file.read()
        video_base64 = base64.b64encode(video_data).decode("utf-8")
    return fastapi.responses.JSONResponse(content={"video_base64": video_base64})

@app.post("/api/difflib")
async def speech_change(
    request: fastapi.Request,
    db: orm.Session = fastapi.Depends(services.get_db)
):
    data = await request.json()
    audio = data.get("data", {}).get("audio")
    jwt = data.get("data", {}).get("jwt")
    original = data.get("data", {}).get("question")

    userid = await services.get_user_id(db,jwt)

    file_path = await services.save_temp_audio(userid, audio)
    new_file = f"{userid}.wav"
    result = await services.convert_mp4_to_wav(file_path, os.path.join('.', 'temp', new_file))
    speakder = await services.get_tts(result)

    truth = re.findall(r"[\w']+", str(original).lower())
    speech = re.findall(r"[\w']+", str(speakder).lower())

    matcher = difflib.SequenceMatcher(None, truth, speech)
    similarity = int(matcher.ratio() * 100)

    for d in difflib.ndiff(truth, speech):
        print(d)

    differences = list(difflib.ndiff(truth, speech))
    return {"differences": differences, "similarity": similarity}


@app.post("/api/test")
async def test(
    email: str = fastapi.Form(...), 
    name: str = fastapi.Form(...),
    password: str = fastapi.Form(...),
    image: str = fastapi.Form(...)
):
    print(email)
    print(name)
    print(password)
    print(image)

@app.get("/api/users/me", response_model=schemas.User)
async def get_user(user: schemas.User = fastapi.Depends(services.get_current_user)):
    return user
