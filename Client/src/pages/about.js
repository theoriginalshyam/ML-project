import React from "react";
import Navbar from "../Mycomps/Navbar";
import Footerc from "../Mycomps/Footer";
import "../stylesheets/About.css"; // Import the CSS file

function About() {
  return (
    <div>
      <Navbar />
      <div>
        <div className="about-section">
          <h1>About Us</h1>
          <p>
            "Our Company StockScope comprises of five talented and
            motivated individuals, each bringing a unique set of skills and
            qualities to the group. It aims to make the process of trading stocks a little
            less daunting by using the power of Artificial Intelligence. We have
            to tried to predict stock prices and movement using LSTM Neural
            Network to predict future prices of the stock and BERTA model and
            Technical Analysis to predict the future movement of price."
          </p>
          <p></p>
        </div>

        <h2
          style={{ textAlign: "center", fontSize: "35px", color: "white" }}
          aaa
        >
          <u />
          <br></br>
          Meet Our Team
          <br></br>
          <br></br>
          <u />
        </h2>

      </div>
      <Footerc />
    </div>
  );
}

export default About;
