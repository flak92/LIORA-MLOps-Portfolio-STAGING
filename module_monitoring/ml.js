/* ML Research and ML Assets tabs: two fetches — /store_status/ml_status.json and
   /store_status/features_status.json (the catalogue frame) — feed the cross-section
   table, the catalogue frame, the five summary views and — through
   asset.js — the per-asset panel. Classic script using appendCell, appendHeaderRow,
   appendRows, renderTable, buildMeter, buildTickerLink, formatCount,
   formatNumber and formatPercent from page.js. */
"use strict";

const CLASS_NAMES = ["short", "neutral", "long"];
let ML_STATUS = null;
let FEATURES_STATUS = null;

function buildShareCell(part, whole) {
  const pctValue = whole ? (100 * part) / whole : 0;
  const wrap = document.createElement("span");
  wrap.appendChild(buildMeter(pctValue));
  wrap.appendChild(document.createTextNode(formatCount(part) + " (" + pctValue.toFixed(1) + "%)"));
  return wrap;
}

function mean(values) {
  return values.reduce((a, b) => a + b, 0) / values.length;
}

function validationFolds(asset) {
  return Object.keys(asset.validation).sort();
}

/* ---- ML Research tab: the wide cross-section table ---- */

function renderResearch(mlStatus) {
  renderTable("ml-assets",
    ["asset", "decisions", "classes &minus;/0/+", "depth/eta/rounds", "prior LL", "model LL",
     "skill", "&tau; (entry edge threshold)", "Sharpe", "maxDD", "trades", "hit", "exposure"],
    mlStatus.assets.map((asset) => {
      const finalHoldoutStrategy = asset.strategy.final_holdout;
      const bestParameters = asset.hyperparameter_search_result.best_params;
      return [
        asset.ticker, formatCount(asset.sample.decision_count),
        formatCount(asset.sample.class_counts.short) + "/" + formatCount(asset.sample.class_counts.neutral)
          + "/" + formatCount(asset.sample.class_counts.long),
        bestParameters.max_depth + " / " + bestParameters.eta.toFixed(3) + " / " + bestParameters.num_boost_round,
        asset.final_holdout.prior_logloss.toFixed(4), asset.final_holdout.model_logloss.toFixed(4),
        formatPercent(asset.final_holdout.relative_logloss_skill, 2),
        asset.strategy.entry_edge_threshold.toFixed(2) + (asset.strategy.entry_edge_threshold_constraint_met ? "" : " !"),
        formatNumber(finalHoldoutStrategy.sharpe, 2), formatPercent(finalHoldoutStrategy.max_drawdown, 1),
        formatCount(finalHoldoutStrategy.trade_count), formatPercent(finalHoldoutStrategy.hit_rate, 1),
        formatPercent(finalHoldoutStrategy.exposure, 1),
      ];
    }));
  document.getElementById("ml-assets").hidden = false;
}

/* ---- ML Research tab: the catalogue frame — the register, every definition with its terms and histories, the nesting ---- */

function formatTerm(term) {
  if (term.indicator === null) return term.inputs[0];
  return term.indicator + term.parameter_bars + " (" + term.parameter_word + " " + term.parameter_bars
    + " bars of " + term.inputs.join(", ")
    + (term.output_range === null ? "" : ", output " + term.output_range[0] + "–" + term.output_range[1]) + ")";
}

/* an effective history as a bar on one time scale across every timeframe, so a level's reach is compared by eye */
function buildHistoryCell(hours, longestHours) {
  if (hours === undefined) return "-";
  const wrap = document.createElement("span");
  wrap.appendChild(buildMeter((100 * hours) / longestHours));
  wrap.appendChild(document.createTextNode(hours + " h"));
  return wrap;
}

function renderCatalogue(featuresStatus) {
  const catalogue = featuresStatus.catalogue;
  const timeframes = catalogue.timeframes.map((entry) => entry.timeframe);
  document.getElementById("catalogue-register").textContent =
    catalogue.timeframes.map((entry) =>
      entry.timeframe.padEnd(5) + (entry.duration_ms / MILLISECONDS_PER_SECOND / SECONDS_PER_MINUTE) + " min · "
      + entry.bars_per_day + " bars per day · "
      + (entry.timeframe === catalogue.decision_timeframe ? "the decision timeframe" : entry.ratio_to_lower + "× the level below")
      + " · " + entry.slot).join("\n")
    + "\nwarm-up: " + catalogue.warmup.top_timeframe_bars + " bars of " + timeframes[timeframes.length - 1]
    + " · first decision " + catalogue.warmup.end_utc + " UTC"
    + "\nrows on the decision grid: " + featuresStatus.assets.map((asset) =>
      asset.ticker + " " + timeframes.map((timeframe) => asset.row_count_by_timeframe[timeframe].toLocaleString("en-US")).join(" / ")).join(", ")
    + (featuresStatus.assets.length ? "" : "no asset catalogued yet");
  const longestHours = Math.max(...catalogue.definitions.flatMap((definition) =>
    Object.values(definition.effective_history_hours_by_timeframe)));
  renderTable("catalogue",
    ["definition", "terms", "range", ...timeframes.map((timeframe) => "effective history " + timeframe), "warm-up (bars)", "default set"],
    catalogue.definitions.map((definition) => [
      definition.feature_definition,
      definition.terms.map(formatTerm).join(" · ")
        + (definition.operators.length ? " · " + definition.operators.join(", ") : "")
        + (definition.normaliser ? " · " + definition.normaliser : ""),
      definition.range,
      ...timeframes.map((timeframe) => buildHistoryCell(definition.effective_history_hours_by_timeframe[timeframe], longestHours)),
      formatCount(definition.warmup_bars),
      definition.definition_in_default_set ? "yes" : "-",
    ]));
  document.getElementById("catalogue-nesting").textContent = "nesting — one level, one domain of time: "
    + catalogue.nesting.map((pair) => "longest on " + pair.lower + " " + pair.lower_longest_effective_history_hours
      + " h < shortest on " + pair.upper + " " + pair.upper_shortest_effective_history_hours + " h").join(" · ");
}

/* ---- ML Assets tab: five complementary cross-section views ---- */

function renderLabels(mlStatus) {
  renderTable("cs-labels",
    ["asset", "decisions", "warm-up excluded", "trainable rows", "short", "neutral share",
     "long", "scored (holdout)"],
    mlStatus.assets.map((asset) => {
      const classCounts = asset.sample.class_counts;
      const total = classCounts.short + classCounts.neutral + classCounts.long;
      return [
        buildTickerLink(asset.ticker, selectAsset),
        formatCount(asset.sample.decision_count),
        formatCount(asset.sample.warmup_excluded_decision_count),
        formatCount(asset.sample.trainable_row_count) + " (" + asset.sample.trainable_row_pct.toFixed(3) + "%)",
        formatCount(classCounts.short),
        buildShareCell(classCounts.neutral, total),
        formatCount(classCounts.long),
        formatCount(asset.final_holdout.scored_row_count),
      ];
    }));
}

function renderClassification(mlStatus) {
  const foldKeys = validationFolds(mlStatus.assets[0]);
  renderTable("cs-classification",
    ["asset", ...foldKeys.map((foldKey) => "val skill F" + foldKey.split("_")[1]),
     "mean val skill", "holdout prior LL", "holdout model LL", "holdout skill"],
    mlStatus.assets.map((asset) => {
      const folds = validationFolds(asset);
      const foldSkills = folds.map((foldKey) => asset.validation[foldKey].relative_logloss_skill);
      return [
        buildTickerLink(asset.ticker, selectAsset),
        ...foldSkills.map((skill) => formatPercent(skill, 2)),
        formatPercent(mean(foldSkills), 2),
        asset.final_holdout.prior_logloss.toFixed(4),
        asset.final_holdout.model_logloss.toFixed(4),
        formatPercent(asset.final_holdout.relative_logloss_skill, 2),
      ];
    }));
}

function renderStrategy(mlStatus) {
  renderTable("cs-strategy",
    ["asset", "entry edge threshold", "constraint met", "grid points cleared",
     "median CAGR over cleared", "selection score", "path CAGR", "path Calmar",
     "path maxDD", "path PF", "holdout CAGR", "degradation", "holdout Sharpe",
     "maxDD", "trades", "hit", "avg trade", "exposure", "final equity",
     "exits: upper/lower/vertical/ambiguous"],
    mlStatus.assets.map((asset) => {
      const finalHoldoutStrategy = asset.strategy.final_holdout;
      const validationPath = asset.strategy.validation_path;
      const selectionScore = asset.strategy.selection_score_cagr_validation_path;
      const holdoutDegradation = finalHoldoutStrategy.cagr === null || validationPath.cagr === null
        ? null : finalHoldoutStrategy.cagr - validationPath.cagr;
      const exitCounts = finalHoldoutStrategy.exit_counts;
      return [
        buildTickerLink(asset.ticker, selectAsset),
        asset.strategy.entry_edge_threshold.toFixed(2),
        asset.strategy.entry_edge_threshold_constraint_met ? "yes" : "fallback",
        asset.strategy.cleared_point_count === null ? "-" : String(asset.strategy.cleared_point_count),
        formatPercent(asset.strategy.median_cagr_over_cleared, 2),
        formatPercent(selectionScore, 2),
        formatPercent(validationPath.cagr, 2),
        formatNumber(validationPath.calmar, 2),
        formatPercent(validationPath.max_drawdown, 1),
        formatNumber(validationPath.profit_factor, 2),
        formatPercent(finalHoldoutStrategy.cagr, 2),
        holdoutDegradation === null ? "-" : (holdoutDegradation >= 0 ? "+" : "") + (100 * holdoutDegradation).toFixed(2) + " pp",
        formatNumber(finalHoldoutStrategy.sharpe, 2),
        formatPercent(finalHoldoutStrategy.max_drawdown, 1),
        formatCount(finalHoldoutStrategy.trade_count),
        formatPercent(finalHoldoutStrategy.hit_rate, 1),
        formatPercent(finalHoldoutStrategy.average_trade_return, 3),
        formatPercent(finalHoldoutStrategy.exposure, 1),
        formatNumber(finalHoldoutStrategy.final_equity, 3),
        exitCounts.upper_barrier + "/" + exitCounts.lower_barrier + "/" + exitCounts.vertical + "/" + exitCounts.ambiguous,
      ];
    }));
}

function renderSearch(mlStatus) {
  renderTable("cs-search",
    ["asset", "trials", "best path CAGR", "depth", "eta",
     "min child", "subsample", "colsample", "lambda", "alpha", "rounds"],
    mlStatus.assets.map((asset) => {
      const bestParameters = asset.hyperparameter_search_result.best_params;
      return [
        buildTickerLink(asset.ticker, selectAsset),
        asset.hyperparameter_search_result.trial_count,
        formatPercent(asset.hyperparameter_search_result.best_cagr_validation_path, 2),
        bestParameters.max_depth,
        bestParameters.eta.toFixed(4),
        bestParameters.min_child_weight,
        bestParameters.subsample.toFixed(3),
        bestParameters.colsample_bytree.toFixed(3),
        bestParameters.lambda.toFixed(3),
        bestParameters.alpha.toFixed(3),
        bestParameters.num_boost_round,
      ];
    }));
}

/* the asset's feature set — its source and its columns per timeframe — and what the coordinate search found
   beside it; the delta of the best proposal's mean validation skill against the asset's is page arithmetic, like
   the mean validation skill */
function renderFeatureSet(mlStatus) {
  const timeframes = FEATURES_STATUS.catalogue.timeframes.map((entry) => entry.timeframe);
  const meanValidationSkill = (asset) => mean(validationFolds(asset).map((fold) => asset.validation[fold].relative_logloss_skill));
  const deltas = mlStatus.assets.map((asset) => {
    const search = asset.coordinate_search;
    const bestProposal = search && search.inputs_current && search.proposals.length ? search.proposals[0] : null;
    return bestProposal === null ? null : bestProposal.mean_relative_logloss_skill - meanValidationSkill(asset);
  });
  const widestDelta = Math.max(0, ...deltas.filter((delta) => delta !== null));
  renderTable("cs-feature-set",
    ["asset", "source", ...timeframes.map((timeframe) => "columns " + timeframe), "mean val skill", "trials", "rounds", "converged",
     "best proposal &Delta; skill"],
    mlStatus.assets.map((asset, i) => {
      const search = asset.coordinate_search;
      const delta = deltas[i];
      const deltaCell = document.createElement("span");
      if (delta !== null) {
        deltaCell.appendChild(buildMeter(widestDelta > 0 ? (100 * Math.max(0, delta)) / widestDelta : 0));
        deltaCell.appendChild(document.createTextNode((delta >= 0 ? "+" : "") + (100 * delta).toFixed(2) + " pp"));
      } else if (search === null) deltaCell.textContent = "no coordinate search yet";
      else if (!search.inputs_current) deltaCell.textContent = "the search predates the asset's state, its profile or its parameters";
      else deltaCell.textContent = "no proposal";
      return [
        buildTickerLink(asset.ticker, selectAsset),
        asset.feature_set.source,
        ...timeframes.map((timeframe) => formatCount(asset.feature_set.columns_by_timeframe[timeframe].length)),
        formatPercent(meanValidationSkill(asset), 2),
        search === null ? "-" : formatCount(search.trial_count),
        search === null ? "-" : formatCount(search.round_count),
        search === null ? "-" : (search.search_converged ? "yes" : "no"),
        deltaCell,
      ];
    }));
}

function selectAsset(ticker) {
  document.querySelector("#asset-pills button[data-key='" + ticker + "']").click();
}

/* ---- fetch ---- */

const fetchSnapshot = (name) => fetch("/store_status/" + name, { cache: "no-store" })
  .then((response) => { if (!response.ok) throw new Error(name + " HTTP " + response.status); return response.json(); });

Promise.all([fetchSnapshot("ml_status.json"), fetchSnapshot("features_status.json")])
  .then(([mlStatus, featuresStatus]) => {
    const envelope =
      "research window: [" + mlStatus.research_window.start_utc + " .. " + mlStatus.research_window.end_utc + ") UTC\n" +
      "seed:            " + mlStatus.research_window.seed + "\n" +
      "generated:       " + mlStatus.generated_at_utc + " UTC";
    document.getElementById("ml-meta").textContent = envelope;
    document.getElementById("asset-meta").textContent = envelope;

    ML_STATUS = mlStatus;
    FEATURES_STATUS = featuresStatus;
    renderResearch(mlStatus);
    renderCatalogue(featuresStatus);
    renderLabels(mlStatus);
    renderClassification(mlStatus);
    renderStrategy(mlStatus);
    renderSearch(mlStatus);
    renderFeatureSet(mlStatus);
    buildAssetPills(mlStatus);
  })
  .catch((error) => {
    ["ml-meta", "asset-meta"].forEach((id) => {
      const box = document.getElementById(id);
      box.textContent = "could not load the ML snapshots (" + error.message + ") — run `make features-status` and `make ml-status`";
      box.className = "box err";
    });
  });
