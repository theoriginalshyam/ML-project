const mongoose = require('mongoose');
const { toJSON } = require('./plugins');

const tradeSchema = mongoose.Schema(
  {
    date: {
      type: String,
      required: true,
      trim: true,
    },
    ticker: {
      type: String,
      required: true,
      trim: true,
    },
    sharesDelta: {
      type: Number,
      required: true,
      default: 0,
    },
    priceAtTime: {
      type: Number,
      required: true,
      default: 0,
    },
    modelSignal: {
      type: String,
      trim: true,
      default: 'HOLD',
    },
    modelShares: {
      type: Number,
      default: 0,
    },
    userOverride: {
      type: Boolean,
      default: false,
    },
  },
  {
    _id: false,
  }
);

const portfolioSchema = mongoose.Schema(
  {
    user: {
      type: mongoose.SchemaTypes.ObjectId,
      ref: 'User',
      required: true,
      unique: true,
    },
    initialCapital: {
      type: Number,
      required: true,
      default: 1000000,
    },
    confirmedDays: {
      type: [String],
      default: [],
    },
    trades: {
      type: [tradeSchema],
      default: [],
    },
  },
  {
    timestamps: true,
  }
);

portfolioSchema.plugin(toJSON);

const UserPortfolio = mongoose.model('UserPortfolio', portfolioSchema);

module.exports = UserPortfolio;
