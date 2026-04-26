const express = require('express');
const auth = require('../../middlewares/auth');
const validate = require('../../middlewares/validate');
const portfolioValidation = require('../../validations/portfolio.validation');
const portfolioController = require('../../controllers/portfolio.controller');

const router = express.Router();

router.get('/me', auth(), portfolioController.getMyPortfolio);
router.get('/recommendations', auth(), portfolioController.getEnrichedRecommendations);
router.post('/confirm', auth(), validate(portfolioValidation.confirmDay), portfolioController.confirmDay);
router.post('/skip', auth(), validate(portfolioValidation.skipDay), portfolioController.skipDay);
router.get('/simulate', auth(), portfolioController.simulateUserPortfolio);
router.get('/history', auth(), portfolioController.getTradeHistory);

module.exports = router;
