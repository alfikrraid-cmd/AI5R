import {
    AI5R_DASHBOARD_RELEASE
}
from "./dashboard_release";


export function verifyRelease(){

    return (

        AI5R_DASHBOARD_RELEASE.version
        ===
        "1.0.0"

        &&

        AI5R_DASHBOARD_RELEASE.status
        ===
        "FROZEN"

    );

}
