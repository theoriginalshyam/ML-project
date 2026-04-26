import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Home from "./pages/home";
import Login from "./pages/login";
import About from "./pages/about";
import ProtectedRoutes from "./pages/protectedroutes";
import Learn from "./pages/learn";
import News from "./Mycomps/news";
import Loading from "./pages/loading";
import RecommendationsPage from "./pages/recommendations";
import PortfolioPage from "./pages/portfolio";
import HistoryPage from "./pages/history";
function App() {
  return (
    <>
      <Router>
        <Routes>
          <Route path="/" element={<Login />} />
          <Route element={<ProtectedRoutes />}>
            <Route path="/home" element={<Home />} />
            <Route path="/recommendations" element={<RecommendationsPage />} />
            <Route path="/portfolio" element={<PortfolioPage />} />
            <Route path="/history" element={<HistoryPage />} />
            <Route path="/about" element={<About />} />
            <Route path="/learn" element={<Learn />} />
            <Route path="/news" element={<News />} />
            <Route path="/loading" element={<Loading />} />
          </Route>
        </Routes>
      </Router>
    </>
  );
}

export default App;
