from pytba import api as tba
import pickle
import requests
from frc_trueskill import FrcTrueSkill
HEADERS = {"X-TBA-App-Id": "frc-4774:TrueSkill:1.0", "X-TBA-Auth-Key": "wvPZhSEB4HaOZ5cyWx4shlOnVR3xfcX5XHMritETGlX1pJhimjrcy7CEmlgTlzEg"}

events = sorted(requests.get('http://www.thebluealliance.com/api/v3/events/2017', headers=HEADERS).json(), key=lambda x: x["start_date"])

tba.set_api_key("frc-4774", "TrueSkill", "1.0")

matches = []
import os.path
if os.path.isfile("matches.p"):
    matches = pickle.load( open( "matches.p", "rb" ) )
    print("Retrieved matches from disk.")
else:
    print("Retrieving matches from Blue Alliance...")
    for event in events:
        try:
            matches += sorted(tba.event_get(event['key']).matches, key=lambda x: x["time"])
            print("Got matches for: %s" % (event['key']))
        except TypeError:
            break

    matches = sorted(matches, key=lambda x: x["time"])
    pickle.dump( matches, open( "matches.p", "wb" ) )
    print("Matches saved on disk.")

trueskill = FrcTrueSkill(predict_previous = False)

# where prediction is chance that RED will win
predictions = []
absolute_predictions = []
results = []
brier = 0
correct = 0
print("Running Predictions...")
for match in matches:
    score = trueskill.correct_scores(match)
    result = None
    if score.red > score.blue:
        result = 1
    elif score.blue > score.red:
        result = 0
    else:
        result = 0.5
    results.append(result)
    red_teams = [int(x[3:]) for x in match['alliances']['red']['teams']]
    blue_teams = [int(x[3:]) for x in match['alliances']['blue']['teams']]
    trueskill.init_teams(red_teams, blue_teams)
    prediction = trueskill.predict(red_teams, blue_teams)
    # print("Prediction %s, result %s" % (prediction, result))
    predictions.append(prediction)
    trueskill.update(match)
    brier += (prediction-result)**2
    absolute_prediction = round(prediction)
    correct += 1 if absolute_prediction == result else 0

print("Computing brier score...")
# calculate brier score
brier *= 1/len(matches)
print(brier)

print("Computing accuracy...")
print(correct/len(matches))
