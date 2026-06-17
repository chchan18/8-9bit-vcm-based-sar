
let((cell cdf sym sym2 cv i15 ahdlResult symPortOrder termMapping viewProps)
  cell = ddGetObj("SAR9B_400MV" "DAC9b_va")
  unless(cell error("missing SAR9B_400MV/DAC9b_va"))
  cdf = cdfGetBaseCellCDF(cell)
  unless(cdf cdf = cdfCreateBaseCellCDF(cell))

  unless(cdfFindParamByName(cdf "VFS")
    cdfCreateParam(
      cdf
      ?name "VFS"
      ?prompt "VFS"
      ?defValue "0.9"
      ?type "string"
      ?parseAsNumber "yes"
      ?parseAsCEL "yes"
      ?display "artParameterInToolDisplay('VFS)"))

  unless(cdfFindParamByName(cdf "VTH")
    cdfCreateParam(
      cdf
      ?name "VTH"
      ?prompt "VTH"
      ?defValue "0.45"
      ?type "string"
      ?parseAsNumber "yes"
      ?parseAsCEL "yes"
      ?display "artParameterInToolDisplay('VTH)"))

  unless(cdfFindParamByName(cdf "trise")
    cdfCreateParam(
      cdf
      ?name "trise"
      ?prompt "trise"
      ?defValue "1e-09"
      ?type "string"
      ?parseAsNumber "yes"
      ?parseAsCEL "yes"
      ?display "artParameterInToolDisplay('trise)"))

  unless(cdfFindParamByName(cdf "tfall")
    cdfCreateParam(
      cdf
      ?name "tfall"
      ?prompt "tfall"
      ?defValue "1e-09"
      ?type "string"
      ?parseAsNumber "yes"
      ?parseAsCEL "yes"
      ?display "artParameterInToolDisplay('tfall)"))

  unless(cdfFindParamByName(cdf "td")
    cdfCreateParam(
      cdf
      ?name "td"
      ?prompt "td"
      ?defValue "0"
      ?type "string"
      ?parseAsNumber "yes"
      ?parseAsCEL "yes"
      ?display "artParameterInToolDisplay('td)"))

  unless(cdfFindParamByName(cdf "rout")
    cdfCreateParam(
      cdf
      ?name "rout"
      ?prompt "rout"
      ?defValue "1"
      ?type "string"
      ?parseAsNumber "yes"
      ?parseAsCEL "yes"
      ?display "artParameterInToolDisplay('rout)"))
  termMapping = list(nil)
  foreach(term list("b8" "b7" "b6" "b5" "b4" "b3" "b2" "b1" "b0" "vdd" "out")
    termMapping = append(termMapping list(concat(term) strcat("\\:" term))))
  viewProps = list(nil)
  viewProps = append(viewProps list('termMapping termMapping))
  viewProps = append(viewProps list('moduleName "DAC9b_va"))
  viewProps = append(viewProps list('namePrefix "ahdl"))
  viewProps = append(viewProps list('termOrder list("out" "vdd" "b0" "b1" "b2" "b3" "b4" "b5" "b6" "b7" "b8")))
  viewProps = append(viewProps list('stringParameterList nil))
  viewProps = append(viewProps list('parameterList list('VFS 'VTH 'trise 'tfall 'td 'rout)))
  cdf~>propList = list('viewInfo list(nil 'veriloga viewProps))
  cdfSaveCDF(cdf)
  sym = dbOpenCellViewByType("SAR9B_400MV" "DAC9b_va" "symbol" "" "a")
  unless(sym error("cannot open DAC9 symbol"))
  dbReplaceProp(sym "portOrder" "ILList" list("out" "vdd" "b0" "b1" "b2" "b3" "b4" "b5" "b6" "b7" "b8"))
  dbReplaceProp(sym "pin#" "int" length(list("out" "vdd" "b0" "b1" "b2" "b3" "b4" "b5" "b6" "b7" "b8")))
  dbSave(sym)
  dbClose(sym)
  ddSetForcedLib("SAR9B_400MV")
  ahdlResult = errset(ahdlUpdateViewInfo("DAC9b_va") nil)
  cv = dbOpenCellViewByType("SAR9B_400MV" "ADC_9B_tb_best_q4" "schematic" "" "a")
  when(cv
    i15 = dbGetInstByName(cv "I15")
    when(i15 cdfUpdateInstParam(i15))
    schCheck(cv)
    dbSave(cv)
    dbClose(cv))
  sym2 = dbOpenCellViewByType("SAR9B_400MV" "DAC9b_va" "symbol" "" "r")
  symPortOrder = if(sym2 sym2~>portOrder nil)
  when(sym2 dbClose(sym2))
  list("cdf_propList" cdf~>propList
       "ahdlUpdate" ahdlResult
       "symbol_portOrder" symPortOrder))
