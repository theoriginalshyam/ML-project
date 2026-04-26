import api from "./http";

export const getEnsembleStatus = async () => (await api.post("/ensemble/status")).data;

export const getEnsembleRecommendations = async () =>
  (await api.post("/ensemble/recommendations")).data;

export const getEnsemblePortfolio = async () => (await api.post("/ensemble/portfolio")).data;
