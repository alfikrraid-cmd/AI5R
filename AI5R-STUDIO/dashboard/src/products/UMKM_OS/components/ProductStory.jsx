import {
    UMKM_PRODUCT_STORY
}
from "../story/productStory";



export default function ProductStory(){


    const story =
    UMKM_PRODUCT_STORY;



    return (

        <div className="card">


            <h2>
                🌱 Product Story
            </h2>


            <h3>
                {story.title}
            </h3>


            <p>
                <b>Problem:</b>
                {" "}
                {story.problem}
            </p>


            <p>
                <b>Solution:</b>
                {" "}
                {story.solution}
            </p>


            <h4>
                How It Works
            </h4>


            {
                story.how_it_works.map(
                    item => (

                        <p key={item}>
                            ⚙️ {item}
                        </p>

                    )
                )
            }


            <p>
                <b>Impact:</b>
                {" "}
                {story.impact}
            </p>


            <p>
                🚀 {story.action}
            </p>


        </div>

    );

}
