const httpStatus = require('http-status');
const ApiError = require('../utils/ApiError');
const catchAsync = require('../utils/catchAsync');
const { UserPortfolio } = require('../models');
const { postMl } = require('../utils/mlClient');

const BUY_MULTIPLIER = 1.001;
const SELL_MULTIPLIER = 0.999;

const ensurePortfolio = async (userId) => {
  let portfolio = await UserPortfolio.findOne({ user: userId });
  if (!portfolio) {
    portfolio = await UserPortfolio.create({ user: userId });
  }
  return portfolio;
};

const buildPortfolioSnapshot = (portfolio) => {
  const holdings = {};
  let balance = Number(portfolio.initialCapital || 1000000);

  (portfolio.trades || []).forEach((trade) => {
    const ticker = trade.ticker;
    const delta = Number(trade.sharesDelta || 0);
    const price = Number(trade.priceAtTime || 0);
    holdings[ticker] = (holdings[ticker] || 0) + delta;
    if (delta > 0) {
      balance -= delta * price * BUY_MULTIPLIER;
    } else if (delta < 0) {
      balance += Math.abs(delta) * price * SELL_MULTIPLIER;
    }
  });

  Object.keys(holdings).forEach((ticker) => {
    if (holdings[ticker] === 0) {
      delete holdings[ticker];
    }
  });

  return {
    holdings,
    balance,
  };
};

const groupHistory = (trades) => {
  const grouped = {};
  let followed = 0;
  let overridden = 0;

  trades.forEach((trade) => {
    const month = trade.date.slice(0, 7);
    if (!grouped[month]) {
      grouped[month] = [];
    }
    grouped[month].push(trade);
    if (trade.userOverride) {
      overridden += 1;
    } else {
      followed += 1;
    }
  });

  const months = Object.keys(grouped)
    .sort()
    .map((month) => ({
      month,
      trades: grouped[month].sort((a, b) => a.date.localeCompare(b.date) || a.ticker.localeCompare(b.ticker)),
    }));

  return {
    months,
    summary: {
      totalTrades: trades.length,
      followed,
      overridden,
      followRate: trades.length ? Number(((followed / trades.length) * 100).toFixed(1)) : 0,
    },
  };
};

const getMyPortfolio = catchAsync(async (req, res) => {
  const portfolio = await ensurePortfolio(req.user.id);
  const snapshot = buildPortfolioSnapshot(portfolio);
  res.send({
    portfolio,
    holdings: snapshot.holdings,
    remainingCash: snapshot.balance,
  });
});

const getEnrichedRecommendations = catchAsync(async (req, res) => {
  const portfolio = await ensurePortfolio(req.user.id);
  const snapshot = buildPortfolioSnapshot(portfolio);
  const recommendationsPayload = await postMl('/ensemble/recommendations');
  const rows = recommendationsPayload.recommendations.map((item) => {
    const currentlyHeld = snapshot.holdings[item.ticker] || 0;
    const buyCost = item.shares > 0 ? item.shares * item.price * BUY_MULTIPLIER : 0;
    return {
      ...item,
      currentlyHeld,
      remainingCash: snapshot.balance,
      wouldExceedBudget: item.shares > 0 ? buyCost > snapshot.balance : false,
    };
  });

  res.send({
    date: recommendationsPayload.date,
    agent: recommendationsPayload.agent,
    regime: recommendationsPayload.regime,
    confirmedDays: portfolio.confirmedDays,
    remainingCash: snapshot.balance,
    holdings: snapshot.holdings,
    recommendations: rows,
  });
});

const confirmDay = catchAsync(async (req, res) => {
  const { date, trades } = req.body;
  const portfolio = await ensurePortfolio(req.user.id);
  if (portfolio.confirmedDays.includes(date)) {
    throw new ApiError(httpStatus.BAD_REQUEST, 'This trading day has already been confirmed');
  }

  const recommendationPayload = await postMl('/ensemble/recommendations');
  if (recommendationPayload.date !== date) {
    throw new ApiError(
      httpStatus.BAD_REQUEST,
      `Recommendation date mismatch. Expected ${recommendationPayload.date} but received ${date}`
    );
  }

  const byTicker = new Map(recommendationPayload.recommendations.map((row) => [row.ticker, row]));
  const userInput = new Map((trades || []).map((trade) => [trade.ticker, Number(trade.sharesDelta || 0)]));
  const normalized = recommendationPayload.recommendations.map((row) => ({
    ticker: row.ticker,
    sharesDelta: userInput.has(row.ticker) ? userInput.get(row.ticker) : Number(row.shares || 0),
    recommendation: row,
  }));

  const snapshot = buildPortfolioSnapshot(portfolio);
  const holdings = { ...snapshot.holdings };
  let balance = snapshot.balance;

  normalized
    .filter((row) => row.sharesDelta < 0)
    .forEach((row) => {
      const held = holdings[row.ticker] || 0;
      if (Math.abs(row.sharesDelta) > held) {
        throw new ApiError(httpStatus.BAD_REQUEST, `Cannot sell more ${row.ticker} shares than currently held`);
      }
      holdings[row.ticker] = held + row.sharesDelta;
      balance += Math.abs(row.sharesDelta) * row.recommendation.price * SELL_MULTIPLIER;
    });

  normalized
    .filter((row) => row.sharesDelta > 0)
    .forEach((row) => {
      const cost = row.sharesDelta * row.recommendation.price * BUY_MULTIPLIER;
      if (cost > balance) {
        throw new ApiError(httpStatus.BAD_REQUEST, `Insufficient cash to buy ${row.sharesDelta} shares of ${row.ticker}`);
      }
      holdings[row.ticker] = (holdings[row.ticker] || 0) + row.sharesDelta;
      balance -= cost;
    });

  const tradeRecords = normalized.map((row) => {
    const recommendation = byTicker.get(row.ticker);
    return {
      date,
      ticker: row.ticker,
      sharesDelta: row.sharesDelta,
      priceAtTime: recommendation.price,
      modelSignal: recommendation.signal,
      modelShares: recommendation.shares,
      userOverride: row.sharesDelta !== recommendation.shares,
    };
  });

  portfolio.trades.push(...tradeRecords);
  portfolio.confirmedDays.push(date);
  await portfolio.save();

  res.status(httpStatus.CREATED).send({
    date,
    tradesSaved: tradeRecords.length,
    remainingCash: balance,
    holdings,
  });
});

const skipDay = catchAsync(async (req, res) => {
  const { date } = req.body;
  const portfolio = await ensurePortfolio(req.user.id);
  if (portfolio.confirmedDays.includes(date)) {
    throw new ApiError(httpStatus.BAD_REQUEST, 'This trading day has already been confirmed');
  }
  portfolio.confirmedDays.push(date);
  await portfolio.save();
  res.status(httpStatus.CREATED).send({ date, skipped: true });
});

const simulateUserPortfolio = catchAsync(async (req, res) => {
  const portfolio = await ensurePortfolio(req.user.id);
  const [userSimulation, modelPortfolio] = await Promise.all([
    postMl('/ensemble/simulate', {
      trades: portfolio.trades.map((trade) => ({
        date: trade.date,
        ticker: trade.ticker,
        sharesDelta: trade.sharesDelta,
      })),
      initialCapital: portfolio.initialCapital,
    }),
    postMl('/ensemble/portfolio'),
  ]);

  const history = groupHistory(portfolio.trades);

  res.send({
    user: userSimulation,
    model: modelPortfolio,
    summary: history.summary,
    confirmedDays: portfolio.confirmedDays,
  });
});

const getTradeHistory = catchAsync(async (req, res) => {
  const portfolio = await ensurePortfolio(req.user.id);
  res.send(groupHistory(portfolio.trades));
});

module.exports = {
  getMyPortfolio,
  getEnrichedRecommendations,
  confirmDay,
  skipDay,
  simulateUserPortfolio,
  getTradeHistory,
};
