import base64
from unittest import result
import fastapi as fastapi
import fastapi.security as security
import database as database, models as models, schemas as schemas
import sqlalchemy.orm as orm
import passlib.hash as hash
import jwt 
import os
import azure.cognitiveservices.speech as speechsdk
from ffmpeg import FFmpeg
from PIL import Image
import io

oauth2schema = security.OAuth2PasswordBearer(tokenUrl="/api/token")

JWT_SECRET = "myjwtsecret"

def create_database():
    return database.Base.metadata.create_all(bind=database.engine)

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_user_by_email(email: str, db: orm.Session):
    return db.query(models.User).filter(models.User.email == email).first()

async def create_user(user: schemas.UserCreate, db: orm.Session):
    user_obj = models.User(
        email=user.email, password = user.password
        #hashed_password = hash.bcrypt.hash(user.hashed_password)
    )
    db.add(user_obj)
    db.commit()
    db.refresh(user_obj)
    return user_obj

async def create_user_info(user_info: schemas.UserInfoCreate, db: orm.Session):
    userInfo_obj = models.UserInfo(
        user_id = user_info.user_id, name = user_info.name, avatar_url = user_info.avatar_url
    )
    db.add(userInfo_obj)
    db.commit()
    db.refresh(userInfo_obj)
    return userInfo_obj


async def authenticate_user(email: str, password: str, db: orm.Session):
    user = await get_user_by_email(db=db, email=email)

    if not user:
        return False

    if not user.verify_password(password):
        return False

    return user

async def create_token(user: models.User):
    user_obj = schemas.User.from_orm(user)

    token = jwt.encode(user_obj.dict(), JWT_SECRET)

    return dict(access_token=token, token_type="bearer")

async def get_current_user( db: orm.Session = fastapi.Depends(get_db), token: str = fastapi.Depends(oauth2schema)):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        user = db.query(models.User).get(payload["id"])
    except:
        raise fastapi.HTTPException(
            status_code=401, detail="Invalid Email or Password"
        )

    return schemas.User.from_orm(user)

async def save_uploaded_file(name: str, image: fastapi.UploadFile):
    target_folder = os.path.join("OnlineDB", "UserImage")
    image_binary = base64.b64decode(image)

    image_data = io.BytesIO(image_binary)
    image_pil = Image.open(image_data)
    output_buffer = io.BytesIO()
    image_pil.save(output_buffer, format='PNG')
    image_binary_png = output_buffer.getvalue()

    target_file_path = os.path.join(target_folder, f"{name}.png")
    with open(target_file_path, "wb") as image_file:
        image_file.write(image_binary_png)
    return target_file_path

async def get_user_avatar(db: orm.Session = fastapi.Depends(get_db), token: str = fastapi.Depends(oauth2schema)):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        user = db.query(models.User).get(payload["id"])
        user_info = db.query(models.UserInfo).filter(models.UserInfo.id == user.id).first()
        if user_info:
            avatar = user_info.avatar_url
    except:
        raise fastapi.HTTPException(
            status_code=401, detail="Error to find user avatar"
        )

    return avatar

async def get_audio(word):
    speech_config = speechsdk.SpeechConfig(subscription='0cb1662358a74aa59c07ed47f04050a7', region='eastasia')
    speech_config.speech_synthesis_voice_name='en-US-GuyNeural'
    speech_config.speech_synthesis_voice_speed = 0.8
    speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
    result = speech_synthesizer.speak_text_async(word).get()
    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        output_folder = "voiceGenerator"
        output_file_name = "output_audio.wav"
        output_file_path = os.path.join(output_folder, output_file_name)
        with open(output_file_path, "wb") as audio_file:
            audio_file.write(result.audio_data)
        return output_file_path

async def get_user_id(db: orm.Session = fastapi.Depends(get_db), token: str = fastapi.Depends(oauth2schema)):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        user = db.query(models.User).get(payload["id"])
        id = user.id
    except:
        raise fastapi.HTTPException(
            status_code=401, detail="Error to find user id"
        )
    return id

async def save_temp_audio(name: str, audio: str):
    target_folder = os.path.join(".", "temp")
    file_extension = 'mp4'
    target_file_path = os.path.join(target_folder, f"{name}.{file_extension}")
    audio_binary = base64.b64decode(audio)
    with open(target_file_path, "wb") as audio_file:
            audio_file.write(audio_binary)
    return target_file_path

async def convert_mp4_to_wav(mp4_file_path: str, output_wav_file_path: str):
    ffmpeg = (FFmpeg().option("y").input(mp4_file_path).output(output_wav_file_path,{"codec:a": "pcm_s16le", "format": "wav"}))
    ffmpeg.execute()
    return output_wav_file_path



async def get_tts(file):
    speech_config = speechsdk.SpeechConfig(subscription='0cb1662358a74aa59c07ed47f04050a7', region='eastasia')
    speech_config.speech_recognition_language = "en-US"

    audio_config = speechsdk.audio.AudioConfig(filename=file)
    speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
    speech_recognition_result = speech_recognizer.recognize_once_async().get()

    if speech_recognition_result.reason == speechsdk.ResultReason.RecognizedSpeech:
        print("Recognized: {}".format(speech_recognition_result.text))
        return speech_recognition_result.text
    elif speech_recognition_result.reason == speechsdk.ResultReason.NoMatch:
        return None
    elif speech_recognition_result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = speech_recognition_result.cancellation_details
        if cancellation_details.reason == speechsdk.CancellationReason.Error:
            return None

