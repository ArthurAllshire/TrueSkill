import requests
import pickle
import os.path
import csv
from frc_trueskill import FrcTrueSkill

event = "2017isde1"

matches = None

if os.path.isfile(event+".csv"):
    with open(event+".pickle") as eventpickle:
        pickle.load(eventpickle)
    # matches.sort(key=lambda m: m['time'])
else:
    matches = requests.get("https://www.thebluealliance.com/api/v2/event/"+event+"/matches", headers={"X-TBA-App-Id":"frc-4774:TrueSkill:1.0"})
    matches = matches.json()
    matches.sort(key=lambda m: m['time'])
    with open(event+".pickle", 'wb') as eventpickle:
        pickle.dump(matches, eventpickle)
frc_trueskill = FrcTrueSkill(offline=True)

f = []
o = []

ties_count = 0

for match in matches:
    frc_trueskill.update(match)

frc_trueskill.processed_matches = set()

for match in matches:
    f.append(frc_trueskill.predict(match["alliances"]["red"]["teams"], match["alliances"]["blue"]["teams"])/100)
    scores = frc_trueskill.correct_scores(match)
    outcome = None
    if scores["red"] == -1:
        continue
    if abs(scores["red"] - scores["blue"]) < FrcTrueSkill.draw_deadband:
        outcome = 0.5
        ties_count += 1
    elif scores["red"] > scores["blue"]:
        outcome = 1
    else:
        outcome = 0
    o.append(outcome)
    frc_trueskill.update(match)

print("Red alliance win probabilities: %s" % (f))
squared_errors = [(f_n - o_n)**2 for f_n, o_n in zip(f, o)]

brier_score = sum(squared_errors)/len(squared_errors)

# print("Percent ties %s" % (ties_count/len(o)))
print("Brier score for regional %s: %s" % (event, brier_score))
