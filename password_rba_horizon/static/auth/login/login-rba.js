/* Copyright 2022 Vincent Unsel & Stephan Wiefling

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

(function(){
    "use strict";

    function connect() {
		const wsProtocol = (window.location.protocol === "https:" ? "wss:" : "ws:");
		const wsHost = window.location.host;
		const wsPath = window.location.pathname;
		const url = wsProtocol + "//" + wsHost + "/ws" + wsPath;
		const socket = new WebSocket(url);
		socket.onopen = (event) => {
		    console.log("Connection open and established.");
		}
		socket.onmessage = (event) => {
		    socket.send(event.data);
		}
		socket.onerror = (event) => {
    	        if(socket.readyState === 1) {
			console.error("Error occured in websocket connection.")
    	        }
		}
		socket.onclose = (event) => {
		    console.log(event);
    	        if(event.wasClean) {
			console.log("Connection closed.");
    	        } else {
			console.error(event.reason + " " + event.code)
		    }
		}
	}

    let loginTitle = document.getElementsByClassName("login-title")[0]
    let loginBtn = document.getElementById("loginBtn");
    let passcodeInput = document.getElementById("id_passcode");
    let form = document.querySelector("form[action='/auth/login/']");
    let panelFooter = loginBtn.parentNode

    document.addEventListener("DOMContentLoaded", (event) => {
	connect()
	if (passcodeInput.type === "hidden") {
	    passcodeInput.disabled = "false";
	}
	else{
	    loginTitle.innerText = "Verify Your Identity"
	    loginBtn.innerText = "Continue";
	    let resendText = document.createElement("p");
	    let resendButton = document.createElement("p");
	    resendText.innerText = "Did not receive a message? ";
	    resendText.style.display = "inline";
	    resendButton.innerText = "Re-send code.";
	    resendButton.style.display = "inline";
	    resendButton.style.color = "blue";
	    resendButton.style.cursor = "pointer";
	    resendButton.onclick =  () => {
			passcodeInput.disabled = "true";
			loginBtn.click()
	    }
	    panelFooter.prepend(resendButton)
	    panelFooter.prepend(resendText)
	}
    });

})();
