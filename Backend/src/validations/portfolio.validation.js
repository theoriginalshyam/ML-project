const Joi = require('joi');

const confirmDay = {
  body: Joi.object().keys({
    date: Joi.string().required(),
    trades: Joi.array()
      .items(
        Joi.object().keys({
          ticker: Joi.string().required(),
          sharesDelta: Joi.number().required(),
        })
      )
      .required(),
  }),
};

const skipDay = {
  body: Joi.object().keys({
    date: Joi.string().required(),
  }),
};

module.exports = {
  confirmDay,
  skipDay,
};
