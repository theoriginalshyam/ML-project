const catchAsync = require('../utils/catchAsync');
const { postMl } = require('../utils/mlClient');

const getStatus = catchAsync(async (req, res) => {
  const payload = await postMl('/ensemble/status');
  res.send(payload);
});

const getRecommendations = catchAsync(async (req, res) => {
  const payload = await postMl('/ensemble/recommendations');
  res.send(payload);
});

const getModelPortfolio = catchAsync(async (req, res) => {
  const payload = await postMl('/ensemble/portfolio');
  res.send(payload);
});

module.exports = {
  getStatus,
  getRecommendations,
  getModelPortfolio,
};
