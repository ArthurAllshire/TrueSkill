from trueskill import TrueSkill, Rating, rate, backends
import argparse
import requests
from datetime import datetime, timedelta


class FrcTrueSkill:
    draw_deadband = 20

    def __init__(self, offline=False):
        self.env = TrueSkill(beta=4, draw_probability=0.2)
        self.trueskills = {}
        self.events = {}
        self.processed_matches = set()
        if not offline:
            self.get_previous_matches()

    def init_teams(self, red_alliance, blue_alliance):
        for alliance in [red_alliance, blue_alliance]:
            for team in alliance:
                if not team in self.trueskills:
                    self.trueskills[team] = self.env.Rating()

    def update(self, match_data):
        if match_data['key'] in self.processed_matches:
            return None

        alliances = match_data['alliances']
        self.init_teams(alliances['red']['teams'], alliances['blue']['teams'])
        # Update ratings based on result
        corrected_scores = self.correct_scores(match_data)
        if not corrected_scores:
            return None

        if abs(corrected_scores['red'] - corrected_scores['blue']) < FrcTrueSkill.draw_deadband:  # Tied
            if corrected_scores['red'] == -1:
                return None # No result yet
            ranks = [0, 0]
        elif corrected_scores['red'] > corrected_scores['blue']:  # Red beat blue
            ranks = [0, 1]  # Lower is better
        else:
            ranks = [1, 0]
        new_red, new_blue = self.env.rate([[self.trueskills[number] for number in alliances['red']['teams']],
                                      [self.trueskills[number] for number in alliances['blue']['teams']]], ranks)
        # Store the new values
        new_ratings = new_red + new_blue
        for rating, team_number in zip(new_ratings,
                alliances['red']['teams']+alliances['blue']['teams']):
            self.trueskills[team_number] = rating
        self.processed_matches.add(match_data['key'])
        return ranks

    def predict(self, red_alliance, blue_alliance):
        self.init_teams(red_alliance, blue_alliance)
        a = [self.trueskills[t] for t in red_alliance]
        b = [self.trueskills[t] for t in blue_alliance]
        deltaMu = sum([x.mu for x in a]) - sum([x.mu for x in b])
        sumSigma = sum([x.sigma ** 2 for x in a]) + sum([x.sigma ** 2 for x in b])
        playerCount = len(a) + len(b)
        denominator = (playerCount * (self.env.beta ** 2) + sumSigma) ** 0.5
        return round(backends.cdf(deltaMu / denominator)*100)

    def skill(self, team):
        if not team in self.trueskills:
            self.trueskills[team] = self.env.Rating()
        return self.env.expose(self.trueskills[team])

    def get_teams_at_event(self, event):
        if not event in self.events:
            # We haven't got this one yet
            teams = requests.get("https://www.thebluealliance.com/api/v2/event/"+event+"/teams", headers={"X-TBA-App-Id":"frc-4774:TrueSkill:1.0"})
            teams = teams.json()
            self.events[event] = teams
        return self.events[event]

    def get_previous_matches(self):
        started_events = []
        all_matches = []
        events = requests.get("https://www.thebluealliance.com/api/v2/events/2017", headers={"X-TBA-App-Id":"frc-4774:TrueSkill:1.0"})
        events = events.json()

        for event in events:
            if event['event_type'] > 5:
                continue
            if event['start_date'] <= str(datetime.date(datetime.today()+timedelta(days=1))):
                matches = requests.get("https://www.thebluealliance.com/api/v2/event/"+event['key']+"/matches", headers={"X-TBA-App-Id":"frc-4774:TrueSkill:1.0"})
                matches = matches.json()
                all_matches += matches
        all_matches.sort(key=lambda m: m['time'])

        for match in all_matches:
            self.update(match)

    def correct_scores(self, match):
        alliances = match['alliances']
        red = alliances['red']
        blue = alliances['blue']

        adj_scores = {'red': red['score'], 'blue': blue['score']}

        score = match['score_breakdown']
        if score is None:
            return adj_scores
        # return None

        red_stats = score['red']
        blue_stats = score['blue']

        if red_stats["rotor3Engaged"]:
            adj_scores['red'] += 100
        if red_stats["kPaRankingPointAchieved"]:
            adj_scores['red'] += 20

        if blue_stats["rotor3Engaged"]:
            adj_scores['blue'] += 100
        if blue_stats["kPaRankingPointAchieved"]:
            adj_scores['blue'] += 20

        return adj_scores
