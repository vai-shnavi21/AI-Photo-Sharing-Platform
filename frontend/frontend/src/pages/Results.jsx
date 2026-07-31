import React from "react";

import {useLocation} from "react-router-dom";

import Gallery from "../components/Gallery";

function Results(){

    const location=useLocation();

    const photos=location.state?.photos || [];

    return(

        <div>

            <h2 style={{textAlign:"center"}}>

                Matched Photos

            </h2>

            {

                photos.length===0 ?

                (

                    <h3 style={{textAlign:"center"}}>

                        No Matching Photos Found

                    </h3>

                )

                :

                (

                    <Gallery

                        photos={photos}

                    />

                )

            }

        </div>

    );

}

export default Results;