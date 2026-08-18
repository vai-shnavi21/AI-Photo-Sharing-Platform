import React from "react";
import { Link } from "react-router-dom";

function Home() {

    return (

        <div className="hero-panel">
            <div className="hero-copy">
                <p className="eyebrow">AI Event Photo Sharing</p>
                <h1>Find your event photos instantly with a selfie.</h1>
                <p>Upload event images, then upload a selfie to locate matching moments from the gallery.</p>
                <div className="hero-actions">
                    <Link to="/upload-event"><button className="hero-button">Upload Event Photos</button></Link>
                    <Link to="/upload-selfie"><button className="secondary-button">Upload Selfie</button></Link>
                </div>
            </div>
            <div style={{display:"grid",placeItems:"center"}}>
                <div style={{width:"100%",maxWidth:"500px",borderRadius:"30px",overflow:"hidden",boxShadow:"0 24px 80px rgba(31,35,60,.12)"}}>
                    <img src="https://images.unsplash.com/photo-1515378791036-0648a3ef77b2?auto=format&fit=crop&w=900&q=80" alt="Event photos" style={{width:"100%",display:"block"}} />
                </div>
            </div>
        </div>

    );

}

export default Home;