import api from "./http";

export const getMyPortfolio = async () => (await api.get("/portfolio/me")).data;

export const getPortfolioRecommendations = async () =>
  (await api.get("/portfolio/recommendations")).data;

export const confirmPortfolioDay = async (payload) =>
  (await api.post("/portfolio/confirm", payload)).data;

export const skipPortfolioDay = async (payload) =>
  (await api.post("/portfolio/skip", payload)).data;

export const getPortfolioSimulation = async () => (await api.get("/portfolio/simulate")).data;

export const getPortfolioHistory = async () => (await api.get("/portfolio/history")).data;
