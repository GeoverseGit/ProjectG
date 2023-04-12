class LookupTable:
    Rainbow = 0
    Inverted_Rainbow = 1
    Greyscale = 2
    Inverted_Greyscale = 3

class ColorPreset:
    def UsePreset(actor, preset):
        lut = actor.GetMapper().GetLookupTable()
        if preset == LookupTable.Rainbow:
            lut.SetHueRange(0.666, 0.0)
            lut.SetSaturationRange(1.0, 1.0)
            lut.SetValueRange(1.0, 1.0)
        elif preset == LookupTable.Inverted_Rainbow:
            lut.SetHueRange(0.0, 0.666)
            lut.SetSaturationRange(1.0, 1.0)
            lut.SetValueRange(1.0, 1.0)
        elif preset == LookupTable.Greyscale:
            lut.SetHueRange(0.0, 0.0)
            lut.SetSaturationRange(0.0, 0.0)
            lut.SetValueRange(0.0, 1.0)
        elif preset == LookupTable.Inverted_Greyscale:
            lut.SetHueRange(0.0, 0.666)
            lut.SetSaturationRange(0.0, 0.0)
            lut.SetValueRange(1.0, 0.0)
        lut.Build()
        
        return lut