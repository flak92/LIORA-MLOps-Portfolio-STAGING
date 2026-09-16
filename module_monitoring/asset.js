/* ML Assets tab: the per-asset panel. Classic script — uses buildMeter, buildFrame, buildTable,
   buildKeyValueBox, buildFootnote, formatCount, formatNumber and formatPercent from page.js,
   and buildShareCell, validationFolds, CLASS_NAMES, ML_STATUS and FEATURES_STATUS from ml.js. */
"use strict";

/* single-series line with a dashed reference level; no legend needed, the
   frame title names the series. Native <title> carries the hover summary. */
function buildSparkline(values, baseline, caption) {
  const NS = "http://www.w3.org/2000/svg";
  const W = 700;
  const H = 120;
  const lo = Math.min(baseline, ...values);
  const hi = Math.max(baseline, ...values);
  const span = hi - lo || 1;
  const x = (i) => (W * i) / Math.max(1, values.length - 1);
  const y = (v) => H - ((v - lo) / span) * H;

  const svg = document.createElementNS(NS, "svg");
  svg.setAttribute("viewBox", "0 0 " + W + " " + H);
  svg.setAttribute("preserveAspectRatio", "none");
  svg.setAttribute("class", "spark");
  const tip = document.createElementNS(NS, "title");
  tip.textContent = caption;
  const base = document.createElementNS(NS, "line");
  base.setAttribute("x1", 0);
  base.setAttribute("x2", W);
  base.setAttribute("y1", y(baseline));
  base.setAttribute("y2", y(baseline));
  base.setAttribute("class", "spark__base");
  const line = document.createElementNS(NS, "polyline");
  line.setAttribute("class", "spark__line");
  line.setAttribute("points", values.map((v, i) => x(i).toFixed(1) + "," + y(v).toFixed(1)).join(" "));
  svg.append(tip, base, line);
  return svg;
}

function buildHeaderLine(asset, mlStatus) {
  const line = document.createElement("p");
  line.className = "sub";
  line.textContent = asset.ticker + " · " + mlStatus.research_window.start_utc.slice(0, 7) + " → "
    + mlStatus.research_window.end_utc.slice(0, 7) + " · " + formatCount(asset.sample.decision_count) + " decisions";
  return line;
}

function buildLabelFrame(asset) {
  const frame = buildFrame("LABEL — triple barrier on the canonical 1m path");
  const classCounts = asset.sample.class_counts;
  const total = classCounts.short + classCounts.neutral + classCounts.long;
  frame.body.appendChild(buildTable(["class", "count", "share"], CLASS_NAMES.map((className) => [
    className, formatCount(classCounts[className]), buildShareCell(classCounts[className], total),
  ])));
  frame.body.appendChild(buildKeyValueBox([
    ["trainable rows", formatCount(asset.sample.trainable_row_count) + " of " + formatCount(asset.sample.decision_count)
      + " (" + asset.sample.trainable_row_pct.toFixed(3) + "%)"],
    ["excluded", formatCount(asset.sample.ambiguous_event_count) + " ambiguous · "
      + formatCount(asset.sample.unobservable_entry_count) + " unobservable entry"],
    ["warm-up excluded", formatCount(asset.sample.warmup_excluded_decision_count) + " decisions"],
  ]));
  return frame.frame;
}

function buildModelFrame(asset, mlStatus) {
  const frame = buildFrame("MODEL — skill against the training class prior");
  const bestParameters = asset.hyperparameter_search_result.best_params;
  frame.body.appendChild(buildKeyValueBox([
    ["parameters", "depth " + bestParameters.max_depth + " · eta " + bestParameters.eta.toFixed(4)
      + " · rounds " + bestParameters.num_boost_round + " · subsample " + bestParameters.subsample.toFixed(2)],
    ["search", asset.hyperparameter_search_result.trial_count + " Optuna trials · best F2–F4 path CAGR "
      + formatPercent(asset.hyperparameter_search_result.best_cagr_validation_path, 2)],
  ]));
  const rows = validationFolds(asset).map((foldKey) => ["F" + foldKey.split("_")[1], asset.validation[foldKey]]);
  rows.push(["F" + mlStatus.final_holdout_fold_id + " — final holdout (out-of-sample)", asset.final_holdout]);
  frame.body.appendChild(buildTable(
    ["fold", "prior log-loss", "model log-loss", "rel. skill", "scored rows"],
    rows.map(([label, metrics], i) => {
      const name = document.createElement("span");
      name.textContent = label;
      if (i === rows.length - 1) name.className = "final-holdout";
      return [name, metrics.prior_logloss.toFixed(6), metrics.model_logloss.toFixed(6),
              formatPercent(metrics.relative_logloss_skill, 2), formatCount(metrics.scored_row_count)];
    })));
  frame.body.appendChild(buildFootnote("skill = 1 − model / prior: what the model adds beyond knowing "
    + "how often each class occurs. The prior comes from the training rows of that fold."));
  return frame.frame;
}

function buildStrategyFrame(asset, mlStatus) {
  const frame = buildFrame("STRATEGY — model picks the side, the hierarchy gates it");
  frame.body.appendChild(buildKeyValueBox([
    ["entry edge threshold (τ)", asset.strategy.entry_edge_threshold.toFixed(2) + (asset.strategy.entry_edge_threshold_constraint_met ? "" : "  (fallback)")],
    ["gate", "side = sign(" + mlStatus.trend_gate_feature + ") and at least " + mlStatus.minimum_agreeing_trend_timeframes + " of " + FEATURES_STATUS.catalogue.timeframes.length + " timeframes agree"],
    ["cost per side", formatPercent(asset.strategy.execution_cost_rate_per_trade_side, 2)
      + "  (execution-cost-adjusted, excluding funding)"],
  ]));
  const rows = validationFolds(asset).map((foldKey) => buildPnlRow("F" + foldKey.split("_")[1], asset.strategy.validation[foldKey], false));
  rows.push(buildPnlRow("F" + mlStatus.final_holdout_fold_id + " — final holdout (out-of-sample)", asset.strategy.final_holdout, true));
  frame.body.appendChild(buildTable(
    ["fold", "Sharpe", "maxDD", "trades", "hit rate", "avg trade", "exposure", "final equity"],
    rows));
  const equityCurve = asset.strategy.equity_curve;
  frame.body.appendChild(buildSparkline(equityCurve.equity, 1.0,
    "equity on the final holdout fold; dashed line = 1.0 (flat)"));
  frame.body.appendChild(buildFootnote("final holdout equity: start 1.000 · end "
    + asset.strategy.final_holdout.final_equity.toFixed(3) + " · dashed line = 1.0. Sharpe is annualised "
    + "from the 15m equity series and the drawdown measured on the 1m path, "
    + "both from the starting capital; the curve above is weekly-sampled."));
  return frame.frame;
}

/* the two importances the payload carries per validation fold, in the order the tables show them */
const IMPORTANCE_MEASURES = [
  { key: "gain_importance", label: "gain", format: (value) => formatCount(Math.round(value)) },
  { key: "mean_abs_shap_importance", label: "mean |SHAP|", format: (value) => formatNumber(value, 4) },
];

function buildImportanceCell(value, scaleMax, format) {
  if (value === null) return "-";
  const wrap = document.createElement("span");
  wrap.appendChild(buildMeter(scaleMax > 0 ? (100 * Math.max(0, value)) / scaleMax : 0));
  wrap.appendChild(document.createTextNode(format(value)));
  return wrap;
}

/* one table per timeframe over the catalogue: the set's columns marked, each importance the mean over the
   validation folds of that fold's booster — page arithmetic, like the mean validation skill; a column outside
   the set has no model to be measured on */
function buildFeatureSetFrame(asset, mlStatus) {
  const frame = buildFrame("FEATURE SET — the columns the model saw, and what each was worth on the validation folds");
  frame.body.appendChild(buildKeyValueBox([
    ["source", asset.feature_set.source === "default" ? "default — the catalogue's default set, no promoted file"
      : "promoted — a hand's choice in the asset's feature-set file; the commit history is the record"],
  ]));
  const folds = Object.keys(asset.validation_importance).sort();
  const inSet = new Set(asset.feature_columns);
  FEATURES_STATUS.catalogue.timeframes.forEach((entry) => {
    const timeframe = entry.timeframe;
    const rows = FEATURES_STATUS.catalogue.definitions
      .filter((definition) => definition.timeframes.includes(timeframe))
      .map((definition) => {
        const column = definition.feature_definition + "_" + timeframe;
        const means = IMPORTANCE_MEASURES.map((measure) => inSet.has(column)
          ? mean(folds.map((fold) => asset.validation_importance[fold][measure.key][column])) : null);
        return { column: column, means: means };
      });
    const scale = IMPORTANCE_MEASURES.map((measure, i) => Math.max(0, ...rows.map((row) => row.means[i] === null ? 0 : row.means[i])));
    frame.body.appendChild(buildTable(
      ["column " + timeframe, "in set", ...IMPORTANCE_MEASURES.map((measure) => measure.label)],
      rows.map((row) => [row.column, inSet.has(row.column) ? "✓" : "-",
        ...row.means.map((value, i) => buildImportanceCell(value, scale[i], IMPORTANCE_MEASURES[i].format))])));
  });
  frame.body.appendChild(buildFootnote("each importance is the mean over folds " + folds.map((fold) => "F" + fold.split("_")[1]).join(", ")
    + " of that fold's own booster: gain is XGBoost total gain, mean |SHAP| the mean absolute contribution in margin space. "
    + "The final holdout attributes nothing."));
  return frame.frame;
}

/* what the coordinate search found: every proposal with what it adds and removes against the active state, the
   validation skill it was chosen on and what the strategy would do with it; the delta against the asset's mean
   validation skill is page arithmetic, like the mean validation skill itself */
function formatColumnChanges(proposal, timeframes) {
  return timeframes.map((timeframe) =>
    proposal.added_columns_by_timeframe[timeframe].map((name) => "+" + name + "_" + timeframe)
      .concat(proposal.removed_columns_by_timeframe[timeframe].map((name) => "\u2212" + name + "_" + timeframe)).join(" "))
    .filter((changes) => changes.length).join(" · ");
}

function buildProposalsFrame(asset, mlStatus) {
  const frame = buildFrame("PROPOSALS — the states the coordinate search found on the validation folds; none is promoted by itself");
  const search = asset.coordinate_search;
  if (search === null) {
    frame.body.appendChild(buildFootnote("no coordinate search yet — run `make ml-coordinate-search ASSET=" + asset.ticker + "`"));
    return frame.frame;
  }
  /* a recorded search conditioned on another set or other parameters compares against a baseline that has gone,
     so the frame states that and shows nothing rather than a delta against the wrong set */
  if (!search.inputs_current) {
    frame.body.appendChild(buildFootnote("the search predates the asset's state, its profile or its parameters — run "
      + "`make ml-coordinate-search ASSET=" + asset.ticker + "`"));
    return frame.frame;
  }
  const timeframes = FEATURES_STATUS.catalogue.timeframes.map((entry) => entry.timeframe);
  const folds = validationFolds(asset);
  const meanValidationSkill = mean(folds.map((fold) => asset.validation[fold].relative_logloss_skill));
  frame.body.appendChild(buildKeyValueBox([
    ["coordinate search", search.trial_count + " trials in " + search.round_count + " rounds · " + (search.search_converged ? "converged" : "not converged")
      + " · the active state's mean validation skill " + formatPercent(meanValidationSkill, 2)],
  ]));
  frame.body.appendChild(buildTable(
    ["#", "trial", "columns added / removed", "path CAGR", "path Calmar", "path PF",
     ...folds.map((fold) => "Calmar F" + fold.split("_")[1]),
     ...folds.map((fold) => "trades F" + fold.split("_")[1]),
     "mean skill", "&Delta; vs active", "&tau;"],
    search.proposals.map((proposal) => {
      const delta = proposal.mean_relative_logloss_skill - meanValidationSkill;
      return [
        proposal.proposal, proposal.trial, formatColumnChanges(proposal, timeframes),
        formatPercent(proposal.validation_path.cagr, 2),
        formatNumber(proposal.validation_path.calmar, 2),
        formatNumber(proposal.validation_path.profit_factor, 2),
        ...folds.map((fold) => formatNumber(proposal.validation[fold].calmar, 2)),
        ...folds.map((fold) => formatCount(proposal.validation[fold].trade_count)),
        formatPercent(proposal.mean_relative_logloss_skill, 2),
        (delta >= 0 ? "+" : "") + (100 * delta).toFixed(2) + " pp",
        proposal.entry_edge_threshold.toFixed(2) + (proposal.entry_edge_threshold_constraint_met ? "" : " !"),
      ];
    })));
  frame.body.appendChild(buildFootnote("every proposal is a trial no validation fold scores below the state the search "
    + "started from; they are ranked by the CAGR of the validation path — F2, F3 and F4 chained into one "
    + "walk-forward equity — and a move reached one only by raising the Calmar ratio of every fold, under the trade "
    + "floor, at its own entry edge threshold (τ marked ! when that floor was not met). When a family accepted a "
    + "state, that state stands first. The model's own skill is reported beside them and was not selected on. "
    + "Nothing here touched the final holdout."));
  return frame.frame;
}

function renderAsset(ticker) {
  const mlStatus = ML_STATUS;
  const host = document.getElementById("asset-detail");
  const asset = mlStatus.assets.find((candidate) => candidate.ticker === ticker);
  host.textContent = "";
  host.appendChild(buildHeaderLine(asset, mlStatus));
  [buildLabelFrame(asset), buildModelFrame(asset, mlStatus), buildStrategyFrame(asset, mlStatus), buildFeatureSetFrame(asset, mlStatus),
   buildProposalsFrame(asset, mlStatus)]
    .forEach((el) => host.appendChild(el));
}

function buildPnlRow(label, pnlMetrics, isFinalHoldout) {
  const name = document.createElement("span");
  name.textContent = label;
  if (isFinalHoldout) name.className = "final-holdout";
  return [
    name,
    formatNumber(pnlMetrics.sharpe, 2),
    formatPercent(pnlMetrics.max_drawdown, 1),
    formatCount(pnlMetrics.trade_count),
    formatPercent(pnlMetrics.hit_rate, 1),
    formatPercent(pnlMetrics.average_trade_return, 3),
    formatPercent(pnlMetrics.exposure, 2),
    formatNumber(pnlMetrics.final_equity, 4),
  ];
}

function buildAssetPills(mlStatus) {
  const group = document.getElementById("asset-pills");
  mlStatus.assets.forEach((asset, i) => {
    const button = document.createElement("button");
    button.className = "pill" + (i === 0 ? " pill--active" : "");
    button.dataset.key = asset.ticker;
    button.textContent = asset.ticker;
    group.appendChild(button);
  });
  PILL_HOOKS.asset = renderAsset;
  /* pills arrive after load, so select here; #TICKER deep-links one asset */
  const wanted = decodeURIComponent(location.hash.slice(1)).toUpperCase();
  const start = group.querySelector("button[data-key='" + wanted + "']")
    || group.querySelector("button");
  if (start) start.click();
}
