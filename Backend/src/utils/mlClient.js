const httpStatus = require('http-status');
const request = require('request');
const ApiError = require('./ApiError');

const ML_BASE_URL = process.env.ML_SERVICE_URL || 'http://localhost:6969';

const postMl = (path, body = {}) =>
  new Promise((resolve, reject) => {
    request.post(
      {
        url: `${ML_BASE_URL}${path}`,
        json: true,
        body,
        headers: {
          Token: `${process.env.SERVER_SECRET}`,
        },
      },
      (err, response, responseBody) => {
        if (err) {
          reject(new ApiError(httpStatus.BAD_GATEWAY, 'ML service unavailable'));
          return;
        }
        if (response.statusCode >= 400) {
          reject(
            new ApiError(
              response.statusCode,
              responseBody?.message || responseBody?.error || 'ML service request failed'
            )
          );
          return;
        }
        resolve(responseBody);
      }
    );
  });

module.exports = {
  postMl,
};
