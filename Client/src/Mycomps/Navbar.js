import React from "react";
import { NavLink, useNavigate } from "react-router-dom";

export default function Navbar() {
  let navigate = useNavigate();

  const handleLogout = () => {
    localStorage.setItem("token", "");
    localStorage.setItem("name", "");
    localStorage.setItem("email", "");
    navigate("/");
  };

  const userName = (localStorage.getItem("name") || "").replace(/"/g, "");

  return (
    <nav className="nav">
      <div className="navbarmain">
        <NavLink to="/home" style={{ textDecoration: "none" }}>
          <h1 style={{ color: "" }}>
            AlgoFlux
          </h1>
        </NavLink>
      </div>
      <div className="navright navbar-links">
        <NavLink className="navbut" to="/home">
          Dashboard
        </NavLink>
        <NavLink className="navbut" to="/recommendations">
          Recommendations
        </NavLink>
        <NavLink className="navbut" to="/portfolio">
          My Portfolio
        </NavLink>
        <NavLink className="navbut" to="/history">
          History
        </NavLink>
        <NavLink className="navbut" to="/news">
          News
        </NavLink>
        <NavLink className="navbut" to="/learn">
          Learn
        </NavLink>
        <NavLink className="navbut" to="/about">
          About
        </NavLink>
        <span className="navbar-user">{userName || "Profile"}</span>
        <button className="navbur" onClick={handleLogout} type="button">
          Logout
        </button>
      </div>
    </nav>
  );
}
