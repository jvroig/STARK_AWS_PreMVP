#STARK Code Generator component.
#Produces the customized static content for a STARK system

#Python Standard Library
import textwrap

def create(data):

    project_name = data["Project Name"]

    source_code = f"""\
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
            <meta http-equiv="content-type" content="text/html; charset=UTF-8" />

            <link rel="stylesheet" href="css/bootstrap.min.css" />
            <link rel="stylesheet" href="css/bootstrap-vue.css" />
            <link rel="stylesheet" href="css/STARK.css" />
            <link rel="stylesheet" href="css/login.css" />

            <script src="js/vue.js" defer></script>
            <script src="js/bootstrap-vue.min.js" defer></script>
            <script src="js/STARK.js" defer></script>
            <script src="js/STARK_spinner.js" defer></script>
            <script src="js/STARK_loading_modal.js" defer></script>
            <script src="js/login.js" defer></script>

            <title>{project_name} :: Login</title>
        </head>
        <body>
        <div class="container-fluid" id="vue-root">

            <div>
                <b-modal id="loading-modal"
                    no-close-on-backdrop
                    no-close-on-esc
                    hide-header
                    hide-footer
                    centered
                    size="sm">
                    <div class="text-center p-3">
                        <div class="spinner-border" style="width: 5rem; height: 5rem" role="status">
                            <span class="sr-only">Loading...</span>
                        </div>
                        <div class="mt-3">
                            Loading...
                        </div>
                    </div>
                </b-modal>
            </div>
            
            <div class="row">
                <div class="col-12 col-md-4"></div>
                <div class="col-12 col-md-4">
                    <b-card 
                        img-src="images/login_06c.png"
                        img-top
                        class="mt-5"
                        title="{project_name}" 
                        sub-title="Please log in to start your adventure.">

                        <div v-html="error_message" class="" v-bind:class="{{'mt-3': authFailure, 'p-3': authFailure, 'text-white': authFailure, 'bg-danger': authFailure, }}"></div>
                        <div v-html="info_message" class="" v-bind:class="{{'mt-3': authTry, 'p-3': authTry, 'text-white': authTry, 'bg-info': authTry }}"></div>

                    <b-form class="pt-3">
                        <b-form-input
                            id="user_name"
                            ref="user_name"
                            v-model="form.username"
                            type="text"
                            placeholder="Username"
                            class="mb-4"
                            size="lg"
                            required
                            v-on:keyup.enter="onUsernameEnter"
                        ></b-form-input>

                        <b-form-input
                            id="user_pass"
                            ref="user_pass"
                            type="password"
                            v-model="form.password"
                            placeholder="Password"
                            class="mb-4"
                            size="lg" 
                            required
                            v-on:keyup.enter="root.submit()"
                        ></b-form-input>
                    
                            <b-button 
                                block 
                                variant="primary" 
                                size="lg"
                                class="mb-3"
                                onClick="root.submit()"
                            >Login</b-button>
                        </b-form>
                    </b-card>
                </div>
                <div class="col-12 col-md-4"></div>
            </div>
        
        </div>
        </body>
        </html>"""

    return textwrap.dedent(source_code)