const express = require('express');
const auth = require('../../middlewares/auth');
const ensembleController = require('../../controllers/ensemble.controller');

const router = express.Router();

router.post('/status', auth(), ensembleController.getStatus);
router.post('/recommendations', auth(), ensembleController.getRecommendations);
router.post('/portfolio', auth(), ensembleController.getModelPortfolio);

module.exports = router;
