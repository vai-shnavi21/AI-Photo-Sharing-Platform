import React from "react";
import { Link } from "react-router-dom";

function Home() {

    return (

        <div style={{textAlign:"center",marginTop:"50px"}}>

            <h1>AI Event Photo Sharing</h1>

            <p>

                Upload event photos, then upload your selfie to find your photos.

            </p>

            <br/>

            <Link to="/upload-event">

                <button>

                    Upload Event Photos

                </button>

            </Link>

            <br/><br/>

            <Link to="/upload-selfie">

                <button>

                    Upload Selfie

                </button>

            </Link>

        </div>

    );

}

export default Home;