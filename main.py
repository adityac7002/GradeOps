from fastapi import FastAPI

# This creates your web app
app = FastAPI()

# This tells the app what to do when someone visits the main page
@app.get("/")
def read_root():
    return {"message": "GradeOps AI Engine is online!"}