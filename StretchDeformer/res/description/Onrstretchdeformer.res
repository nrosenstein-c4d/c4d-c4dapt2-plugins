CONTAINER Onrstretchdeformer
{
    NAME Onrstretchdeformer;
    INCLUDE Obase;

    GROUP ID_OBJECTPROPERTIES
    {
        GROUP
        {
            COLUMNS 2;
            BUTTON NR_STRETCHDEFORMER_BTN_INITIALIZE { }
            BUTTON NR_STRETCHDEFORMER_BTN_FREE { }
        }
        SEPARATOR { LINE; }

        REAL   NR_STRETCHDEFORMER_INNER_RADIUS
        {
            UNIT METER; MIN 0; DEFAULT 100;
        }
        REAL   NR_STRETCHDEFORMER_OUTER_RADIUS
        {
            UNIT METER; MIN 0; DEFAULT 200;
        }

        SPLINE NR_STRETCHDEFORMER_FALLOFF_SPLINE { }
        SPLINE NR_STRETCHDEFORMER_COMPRESS_SPLINE { }

        REAL   NR_STRETCHDEFORMER_COMPRESS_STRENGTH
        {
            CUSTOMGUI REALSLIDER; UNIT PERCENT;
            MINSLIDER 0; MAXSLIDER 100;
        }
        REAL   NR_STRETCHDEFORMER_COMPRESS_MAXDISTANCE
        {
            CUSTOMGUI REALSLIDER; UNIT METER;
            MINSLIDER 0; MAXSLIDER 1000;
            DEFAULT 200;
        }
    }
}