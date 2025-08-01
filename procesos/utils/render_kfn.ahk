Programa := "C:\Program Files\NVH Production\KaraFun Studio 1.20\KaraFunStudio.exe"
TextoEsperado := "Cerrar"
SetTimer, VerificarEstadoPantalla, 1000
nombreSoftware := "KaraFun Studio" ; Reemplaza con el nombre real del software

If (A_Args.Count() > 0) {
	    RutaArchivo := A_Args[1]
        RutaArchivoOutAvi := A_Args[2]
    Run,  %Programa% "%RutaArchivo%"
	    WinWait, ahk_exe %Programa%
	    Send, !axa
        Send, {Tab}
        Send, {Tab}
        Send, {Tab}
        Send, {Space}
        Send, {Tab}
        Send, {Tab}
        Send, {Tab}
        Send, {Tab}
        Send, {Tab}
        Send, {Tab}
        Send, {Tab}
        Send, {Tab}
        Send, {Tab}
        Send, {Tab}
        Send, %RutaArchivoOutAvi%
        Send, {Tab}
        Send, {Enter}
		    Sleep, 180000 
            WinClose, ahk_exe %Programa%
            WinClose, ahk_exe %Programa%
            WinClose, ahk_exe %Programa%
            WinClose, ahk_exe %Programa%
            WinClose, ahk_exe %Programa%
            WinClose, ahk_exe %Programa%
	    return
	
	


} else {
    MsgBox, No se proporcionaron parámetros.
}

VerificarEstadoPantalla:
    ; Captura el texto actual en la pantalla
    WinGetText, TextoActual, A

    ; Verifica si el texto actual coincide con el texto esperado
    if (InStr(TextoActual, "Abrir")&&InStr(TextoActual, "Cerrar")&&InStr(TextoActual, "Explorar...")&&InStr(TextoActual, "Cancelar")){
        ; Realiza acciones adicionales aquí cuando el texto esperado está presente en la pantalla
		
		        WinClose, ahk_exe %Programa%
		        WinClose, ahk_exe %Programa%
                WinClose, ahk_exe %Programa%
                WinClose, ahk_exe %Programa%
                WinClose, ahk_exe %Programa%
                WinClose, ahk_exe %Programa%
                ExitApp
	    return
	    } else{
        ; Realiza acciones adicionales aquí cuando el texto esperado no está presente en la pantalla
        ; Puedes agregar código adicional o simplemente no hacer nada en este caso
    }
return