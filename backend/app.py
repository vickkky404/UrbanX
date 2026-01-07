# importing flask  module  and calling a perticular flask file
from flask import Flask

# creates the instance for the flask  class
#  app = Flask(__name__) determines the class path
app = Flask(__name__)

# The route() decorator tells Flask what URL should trigger the function....
@app.route('/')
def home():
    return "UrbanX Backend Implementation"
#  ///////////////////
# runs the applicaiton
if __name__ == "__main__":
    app.run(debug=True)