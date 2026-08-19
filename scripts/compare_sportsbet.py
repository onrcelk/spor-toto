import pandas as pd, numpy as np, json
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

df = pd.read_parquet('data/real_training.parquet')
feat = ['home_goals_avg','away_goals_avg','home_conceded_avg','away_conceded_avg',
         'home_form_points','away_form_points','h2h_home_win_rate','h2h_draw_rate',
         'h2h_away_win_rate','home_xg_avg','away_xg_avg','rest_days_home','rest_days_away']
X = df[feat].fillna(0).values
y = df['actual_1x2'].values
X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42, shuffle=False)

base = float(pd.Series(y_te).value_counts(normalize=True).max())

gb = GradientBoostingClassifier(random_state=7).fit(X_tr, y_tr)
gb_acc = accuracy_score(y_te, gb.predict(X_te))

# sports-betting Logistic equivalent (one-vs-rest for 3 classes)
logit = LogisticRegression(max_iter=1000).fit(X_tr, y_tr)
logit_acc = accuracy_score(y_te, logit.predict(X_te))

print("Baseline majority:", round(base,4))
print("Our GB acc:", round(gb_acc,4))
print("sports-betting Logit acc:", round(logit_acc,4))
print("Our lift:", round(gb_acc-base,4))

json.dump({
  "baseline_majority": round(base,4),
  "our_model_gb_acc": round(gb_acc,4),
  "sportsbet_logit_acc": round(logit_acc,4),
  "our_lift": round(gb_acc-base,4),
}, open('data/analysis/model_comparison_sportsbet.json','w'), indent=2, ensure_ascii=False)
print("Saved.")
