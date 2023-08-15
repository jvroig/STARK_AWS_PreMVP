#STARK Code Generator component.
#Produces the customized static content for a STARK system

#Python Standard Library
import textwrap

def create(data):

    source_code = f"""\
        var root = new Vue({{
            el: "#vue-root",
            data: {{
                form: {{
                    username: '',
                    password: '',
                }},
                error_message: '',
                info_message: '',
                authFailure: false,
                authTry: false
            }},
            methods: {{

                login: function (payload) {{

                    fetchUrl = STARK.login_url
                    return STARK.request('POST', fetchUrl, payload)
                }},
            
                submit: function () {{
                    root.error_message = ""
                    root.authFailure   = false
                    root.authTry       = true
                    root.info_message  = "Trying to log in..."
                    loading_modal.show()
                    console.log("Logging in!")

                    let data = {{ Login: this.form }}

                    this.login(data).then( function(data) {{
                        console.log("Response received from login endpoint!");
                        loading_modal.hide()
                        console.log(data)

                        //Determine response is success or failure.
                        //If success, create cookie with the supplied session_id
                        //Else, show error message
                        if(data['message'] == 'AuthSuccess') {{
                            console.log('Legit!')
                            localStorage.clear()
                            window.location.href = "home.html";
                        }}
                        else {{
                            console.log("Invalid username or password!")
                            root.authTry       = false
                            root.info_message  = ''
                            root.error_message = "Invalid username or password"
                            root.authFailure   = true
                        }}
        
                    }}).catch(function(error) {{
                        console.log("Encountered an error! [" + error + "]")
                        loading_modal.hide()
                    }});
                }},

                onUsernameEnter: function () {{
                    console.log("Caught ENTER key in username field!")
                    this.$refs["user_pass"].focus()
                }}
            }}
        }})

        window.onload = (event) => {{
            document.getElementById("user_name").focus()
        }};
    """
    return textwrap.dedent(source_code)