import colors from "../../theme/colors";

export default function StatCard({

    title,

    value,

    subtitle,

    color=colors.primary

}){

    return(

        <div style={{

            background:colors.surface,

            border:`1px solid ${colors.border}`,

            borderLeft:`6px solid ${color}`,

            borderRadius:14,

            padding:20,

            transition:".2s"

        }}>

            <div style={{

                color:colors.textMuted,

                fontSize:13,

                textTransform:"uppercase"

            }}>

                {title}

            </div>

            <div style={{

                fontSize:34,

                fontWeight:700,

                marginTop:10

            }}>

                {value}

            </div>

            <div style={{

                color:colors.textMuted,

                marginTop:8

            }}>

                {subtitle}

            </div>

        </div>

    )

}