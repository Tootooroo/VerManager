function _defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ("value" in descriptor) descriptor.writable = true; Object.defineProperty(target, descriptor.key, descriptor); } }

function _createClass(Constructor, protoProps, staticProps) { if (protoProps) _defineProperties(Constructor.prototype, protoProps); if (staticProps) _defineProperties(Constructor, staticProps); return Constructor; }

function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

(window["webpackJsonp"] = window["webpackJsonp"] || []).push([["main"], {
  /***/
  "./$$_lazy_route_resource lazy recursive":
  /*!******************************************************!*\
    !*** ./$$_lazy_route_resource lazy namespace object ***!
    \******************************************************/

  /*! no static exports found */

  /***/
  function $$_lazy_route_resourceLazyRecursive(module, exports) {
    function webpackEmptyAsyncContext(req) {
      // Here Promise.resolve().then() is used instead of new Promise() to prevent
      // uncaught exception popping up in devtools
      return Promise.resolve().then(function () {
        var e = new Error("Cannot find module '" + req + "'");
        e.code = 'MODULE_NOT_FOUND';
        throw e;
      });
    }

    webpackEmptyAsyncContext.keys = function () {
      return [];
    };

    webpackEmptyAsyncContext.resolve = webpackEmptyAsyncContext;
    module.exports = webpackEmptyAsyncContext;
    webpackEmptyAsyncContext.id = "./$$_lazy_route_resource lazy recursive";
    /***/
  },

  /***/
  "./src/app/app.component.ts":
  /*!**********************************!*\
    !*** ./src/app/app.component.ts ***!
    \**********************************/

  /*! exports provided: AppComponent, NavrowComponent */

  /***/
  function srcAppAppComponentTs(module, __webpack_exports__, __webpack_require__) {
    "use strict";

    __webpack_require__.r(__webpack_exports__);
    /* harmony export (binding) */


    __webpack_require__.d(__webpack_exports__, "AppComponent", function () {
      return AppComponent;
    });
    /* harmony export (binding) */


    __webpack_require__.d(__webpack_exports__, "NavrowComponent", function () {
      return NavrowComponent;
    });
    /* harmony import */


    var _angular_core__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(
    /*! @angular/core */
    "./node_modules/@angular/core/__ivy_ngcc__/fesm2015/core.js");
    /* harmony import */


    var _ver_register_ver_register_component__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(
    /*! ./ver-register/ver-register.component */
    "./src/app/ver-register/ver-register.component.ts");
    /* harmony import */


    var _ver_gen_ver_gen_component__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(
    /*! ./ver-gen/ver-gen.component */
    "./src/app/ver-gen/ver-gen.component.ts");
    /* harmony import */


    var _progress_bar_progress_bar_component__WEBPACK_IMPORTED_MODULE_3__ = __webpack_require__(
    /*! ./progress-bar/progress-bar.component */
    "./src/app/progress-bar/progress-bar.component.ts");
    /* harmony import */


    var _angular_material_toolbar__WEBPACK_IMPORTED_MODULE_4__ = __webpack_require__(
    /*! @angular/material/toolbar */
    "./node_modules/@angular/material/__ivy_ngcc__/fesm2015/toolbar.js");

    var AppComponent = function AppComponent() {
      _classCallCheck(this, AppComponent);

      this.title = 'Version Manager';
    };

    AppComponent.ɵfac = function AppComponent_Factory(t) {
      return new (t || AppComponent)();
    };

    AppComponent.ɵcmp = _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵdefineComponent"]({
      type: AppComponent,
      selectors: [["app-root"]],
      decls: 6,
      vars: 0,
      consts: [[1, "GenPanel"]],
      template: function AppComponent_Template(rf, ctx) {
        if (rf & 1) {
          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelement"](0, "navbar-row");

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementStart"](1, "div");

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementStart"](2, "div", 0);

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelement"](3, "app-ver-register");

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelement"](4, "app-ver-gen");

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementEnd"]();

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelement"](5, "app-progress-bar");

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementEnd"]();
        }
      },
      directives: function directives() {
        return [NavrowComponent, _ver_register_ver_register_component__WEBPACK_IMPORTED_MODULE_1__["VerRegisterComponent"], _ver_gen_ver_gen_component__WEBPACK_IMPORTED_MODULE_2__["VerGenComponent"], _progress_bar_progress_bar_component__WEBPACK_IMPORTED_MODULE_3__["ProgressBarComponent"]];
      },
      styles: ["h1[_ngcontent-%COMP%] {\n    font-size: 1.2em;\n    margin-bottom: 0;\n    overflow-y: auto;\n}\n\n.GenPanel[_ngcontent-%COMP%] {\n    display: grid;\n    width: 25cm;\n    grid-template-rows: 3cm 30cm;\n    grid-template-colums: repeat(10, 2cm);\n    margin-left: auto;\n    margin-right: auto;\n}\n\napp-ver-register[_ngcontent-%COMP%] {\n    grid-row-start: 2;\n    grid-column-start: 1;\n    grid-column-end: 4;\n    padding: 1em;\n}\n\napp-ver-gen[_ngcontent-%COMP%] {\n    grid-row-start: 2;\n    grid-column-start: 5;\n    grid-column-end: 8;\n    padding: 1em;\n}\n/*# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJzb3VyY2VzIjpbInNyYy9hcHAvYXBwLmNvbXBvbmVudC5jc3MiXSwibmFtZXMiOltdLCJtYXBwaW5ncyI6IkFBQUE7SUFDSSxnQkFBZ0I7SUFDaEIsZ0JBQWdCO0lBQ2hCLGdCQUFnQjtBQUNwQjs7QUFFQTtJQUNJLGFBQWE7SUFDYixXQUFXO0lBQ1gsNEJBQTRCO0lBQzVCLHFDQUFxQztJQUNyQyxpQkFBaUI7SUFDakIsa0JBQWtCO0FBQ3RCOztBQUVBO0lBQ0ksaUJBQWlCO0lBQ2pCLG9CQUFvQjtJQUNwQixrQkFBa0I7SUFDbEIsWUFBWTtBQUNoQjs7QUFFQTtJQUNJLGlCQUFpQjtJQUNqQixvQkFBb0I7SUFDcEIsa0JBQWtCO0lBQ2xCLFlBQVk7QUFDaEIiLCJmaWxlIjoic3JjL2FwcC9hcHAuY29tcG9uZW50LmNzcyIsInNvdXJjZXNDb250ZW50IjpbImgxIHtcbiAgICBmb250LXNpemU6IDEuMmVtO1xuICAgIG1hcmdpbi1ib3R0b206IDA7XG4gICAgb3ZlcmZsb3cteTogYXV0bztcbn1cblxuLkdlblBhbmVsIHtcbiAgICBkaXNwbGF5OiBncmlkO1xuICAgIHdpZHRoOiAyNWNtO1xuICAgIGdyaWQtdGVtcGxhdGUtcm93czogM2NtIDMwY207XG4gICAgZ3JpZC10ZW1wbGF0ZS1jb2x1bXM6IHJlcGVhdCgxMCwgMmNtKTtcbiAgICBtYXJnaW4tbGVmdDogYXV0bztcbiAgICBtYXJnaW4tcmlnaHQ6IGF1dG87XG59XG5cbmFwcC12ZXItcmVnaXN0ZXIge1xuICAgIGdyaWQtcm93LXN0YXJ0OiAyO1xuICAgIGdyaWQtY29sdW1uLXN0YXJ0OiAxO1xuICAgIGdyaWQtY29sdW1uLWVuZDogNDtcbiAgICBwYWRkaW5nOiAxZW07XG59XG5cbmFwcC12ZXItZ2VuIHtcbiAgICBncmlkLXJvdy1zdGFydDogMjtcbiAgICBncmlkLWNvbHVtbi1zdGFydDogNTtcbiAgICBncmlkLWNvbHVtbi1lbmQ6IDg7XG4gICAgcGFkZGluZzogMWVtO1xufVxuIl19 */"]
    });
    /*@__PURE__*/

    (function () {
      _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵsetClassMetadata"](AppComponent, [{
        type: _angular_core__WEBPACK_IMPORTED_MODULE_0__["Component"],
        args: [{
          selector: 'app-root',
          templateUrl: './app.component.html',
          styleUrls: ['./app.component.css']
        }]
      }], null, null);
    })();

    var NavrowComponent = function NavrowComponent() {
      _classCallCheck(this, NavrowComponent);
    };

    NavrowComponent.ɵfac = function NavrowComponent_Factory(t) {
      return new (t || NavrowComponent)();
    };

    NavrowComponent.ɵcmp = _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵdefineComponent"]({
      type: NavrowComponent,
      selectors: [["navbar-row"]],
      decls: 2,
      vars: 0,
      consts: [["color", "primary", 1, "mat-elevation-z5"]],
      template: function NavrowComponent_Template(rf, ctx) {
        if (rf & 1) {
          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementStart"](0, "mat-toolbar", 0);

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵtext"](1, " Version Manager\n");

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementEnd"]();
        }
      },
      directives: [_angular_material_toolbar__WEBPACK_IMPORTED_MODULE_4__["MatToolbar"]],
      styles: ["mat-toolbar[_ngcontent-%COMP%] {\n    position: fixed;\n    z-index: 10;\n}\n/*# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJzb3VyY2VzIjpbInNyYy9hcHAvbmF2YmFyLXJvdy5jc3MiXSwibmFtZXMiOltdLCJtYXBwaW5ncyI6IkFBQUE7SUFDSSxlQUFlO0lBQ2YsV0FBVztBQUNmIiwiZmlsZSI6InNyYy9hcHAvbmF2YmFyLXJvdy5jc3MiLCJzb3VyY2VzQ29udGVudCI6WyJtYXQtdG9vbGJhciB7XG4gICAgcG9zaXRpb246IGZpeGVkO1xuICAgIHotaW5kZXg6IDEwO1xufVxuIl19 */"]
    });
    /*@__PURE__*/

    (function () {
      _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵsetClassMetadata"](NavrowComponent, [{
        type: _angular_core__WEBPACK_IMPORTED_MODULE_0__["Component"],
        args: [{
          selector: 'navbar-row',
          templateUrl: './navbar-row.html',
          styleUrls: ['./navbar-row.css']
        }]
      }], null, null);
    })();
    /***/

  },

  /***/
  "./src/app/app.module.ts":
  /*!*******************************!*\
    !*** ./src/app/app.module.ts ***!
    \*******************************/

  /*! exports provided: AppModule */

  /***/
  function srcAppAppModuleTs(module, __webpack_exports__, __webpack_require__) {
    "use strict";

    __webpack_require__.r(__webpack_exports__);
    /* harmony export (binding) */


    __webpack_require__.d(__webpack_exports__, "AppModule", function () {
      return AppModule;
    });
    /* harmony import */


    var _angular_platform_browser__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(
    /*! @angular/platform-browser */
    "./node_modules/@angular/platform-browser/__ivy_ngcc__/fesm2015/platform-browser.js");
    /* harmony import */


    var _angular_core__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(
    /*! @angular/core */
    "./node_modules/@angular/core/__ivy_ngcc__/fesm2015/core.js");
    /* harmony import */


    var _angular_common_http__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(
    /*! @angular/common/http */
    "./node_modules/@angular/common/__ivy_ngcc__/fesm2015/http.js");
    /* harmony import */


    var _app_component__WEBPACK_IMPORTED_MODULE_3__ = __webpack_require__(
    /*! ./app.component */
    "./src/app/app.component.ts");
    /* harmony import */


    var _angular_platform_browser_animations__WEBPACK_IMPORTED_MODULE_4__ = __webpack_require__(
    /*! @angular/platform-browser/animations */
    "./node_modules/@angular/platform-browser/__ivy_ngcc__/fesm2015/animations.js");
    /* harmony import */


    var _ver_gen_ver_gen_component__WEBPACK_IMPORTED_MODULE_5__ = __webpack_require__(
    /*! ./ver-gen/ver-gen.component */
    "./src/app/ver-gen/ver-gen.component.ts");
    /* harmony import */


    var _ver_register_ver_register_component__WEBPACK_IMPORTED_MODULE_6__ = __webpack_require__(
    /*! ./ver-register/ver-register.component */
    "./src/app/ver-register/ver-register.component.ts");
    /* harmony import */


    var _angular_material_list__WEBPACK_IMPORTED_MODULE_7__ = __webpack_require__(
    /*! @angular/material/list */
    "./node_modules/@angular/material/__ivy_ngcc__/fesm2015/list.js");
    /* harmony import */


    var _angular_material_expansion__WEBPACK_IMPORTED_MODULE_8__ = __webpack_require__(
    /*! @angular/material/expansion */
    "./node_modules/@angular/material/__ivy_ngcc__/fesm2015/expansion.js");
    /* harmony import */


    var _angular_material_dialog__WEBPACK_IMPORTED_MODULE_9__ = __webpack_require__(
    /*! @angular/material/dialog */
    "./node_modules/@angular/material/__ivy_ngcc__/fesm2015/dialog.js");
    /* harmony import */


    var _angular_material_button__WEBPACK_IMPORTED_MODULE_10__ = __webpack_require__(
    /*! @angular/material/button */
    "./node_modules/@angular/material/__ivy_ngcc__/fesm2015/button.js");
    /* harmony import */


    var _angular_material_input__WEBPACK_IMPORTED_MODULE_11__ = __webpack_require__(
    /*! @angular/material/input */
    "./node_modules/@angular/material/__ivy_ngcc__/fesm2015/input.js");
    /* harmony import */


    var _angular_material_select__WEBPACK_IMPORTED_MODULE_12__ = __webpack_require__(
    /*! @angular/material/select */
    "./node_modules/@angular/material/__ivy_ngcc__/fesm2015/select.js");
    /* harmony import */


    var _angular_material_grid_list__WEBPACK_IMPORTED_MODULE_13__ = __webpack_require__(
    /*! @angular/material/grid-list */
    "./node_modules/@angular/material/__ivy_ngcc__/fesm2015/grid-list.js");
    /* harmony import */


    var _angular_material_toolbar__WEBPACK_IMPORTED_MODULE_14__ = __webpack_require__(
    /*! @angular/material/toolbar */
    "./node_modules/@angular/material/__ivy_ngcc__/fesm2015/toolbar.js");
    /* harmony import */


    var _angular_forms__WEBPACK_IMPORTED_MODULE_15__ = __webpack_require__(
    /*! @angular/forms */
    "./node_modules/@angular/forms/__ivy_ngcc__/fesm2015/forms.js");
    /* harmony import */


    var _progress_bar_progress_bar_component__WEBPACK_IMPORTED_MODULE_16__ = __webpack_require__(
    /*! ./progress-bar/progress-bar.component */
    "./src/app/progress-bar/progress-bar.component.ts");

    var AppModule = function AppModule() {
      _classCallCheck(this, AppModule);
    };

    AppModule.ɵmod = _angular_core__WEBPACK_IMPORTED_MODULE_1__["ɵɵdefineNgModule"]({
      type: AppModule,
      bootstrap: [_app_component__WEBPACK_IMPORTED_MODULE_3__["AppComponent"]]
    });
    AppModule.ɵinj = _angular_core__WEBPACK_IMPORTED_MODULE_1__["ɵɵdefineInjector"]({
      factory: function AppModule_Factory(t) {
        return new (t || AppModule)();
      },
      providers: [],
      imports: [[_angular_platform_browser__WEBPACK_IMPORTED_MODULE_0__["BrowserModule"], _angular_platform_browser_animations__WEBPACK_IMPORTED_MODULE_4__["BrowserAnimationsModule"], _angular_common_http__WEBPACK_IMPORTED_MODULE_2__["HttpClientModule"], _angular_forms__WEBPACK_IMPORTED_MODULE_15__["FormsModule"], _angular_material_list__WEBPACK_IMPORTED_MODULE_7__["MatListModule"], _angular_material_expansion__WEBPACK_IMPORTED_MODULE_8__["MatExpansionModule"], _angular_material_dialog__WEBPACK_IMPORTED_MODULE_9__["MatDialogModule"], _angular_material_button__WEBPACK_IMPORTED_MODULE_10__["MatButtonModule"], _angular_material_input__WEBPACK_IMPORTED_MODULE_11__["MatInputModule"], _angular_material_select__WEBPACK_IMPORTED_MODULE_12__["MatSelectModule"], _angular_material_grid_list__WEBPACK_IMPORTED_MODULE_13__["MatGridListModule"], _angular_material_toolbar__WEBPACK_IMPORTED_MODULE_14__["MatToolbarModule"]]]
    });

    (function () {
      (typeof ngJitMode === "undefined" || ngJitMode) && _angular_core__WEBPACK_IMPORTED_MODULE_1__["ɵɵsetNgModuleScope"](AppModule, {
        declarations: [_app_component__WEBPACK_IMPORTED_MODULE_3__["AppComponent"], _ver_gen_ver_gen_component__WEBPACK_IMPORTED_MODULE_5__["VerGenComponent"], _ver_register_ver_register_component__WEBPACK_IMPORTED_MODULE_6__["RegisterDialog"], _app_component__WEBPACK_IMPORTED_MODULE_3__["NavrowComponent"], _ver_register_ver_register_component__WEBPACK_IMPORTED_MODULE_6__["VerRegisterComponent"], _progress_bar_progress_bar_component__WEBPACK_IMPORTED_MODULE_16__["ProgressBarComponent"]],
        imports: [_angular_platform_browser__WEBPACK_IMPORTED_MODULE_0__["BrowserModule"], _angular_platform_browser_animations__WEBPACK_IMPORTED_MODULE_4__["BrowserAnimationsModule"], _angular_common_http__WEBPACK_IMPORTED_MODULE_2__["HttpClientModule"], _angular_forms__WEBPACK_IMPORTED_MODULE_15__["FormsModule"], _angular_material_list__WEBPACK_IMPORTED_MODULE_7__["MatListModule"], _angular_material_expansion__WEBPACK_IMPORTED_MODULE_8__["MatExpansionModule"], _angular_material_dialog__WEBPACK_IMPORTED_MODULE_9__["MatDialogModule"], _angular_material_button__WEBPACK_IMPORTED_MODULE_10__["MatButtonModule"], _angular_material_input__WEBPACK_IMPORTED_MODULE_11__["MatInputModule"], _angular_material_select__WEBPACK_IMPORTED_MODULE_12__["MatSelectModule"], _angular_material_grid_list__WEBPACK_IMPORTED_MODULE_13__["MatGridListModule"], _angular_material_toolbar__WEBPACK_IMPORTED_MODULE_14__["MatToolbarModule"]]
      });
    })();
    /*@__PURE__*/


    (function () {
      _angular_core__WEBPACK_IMPORTED_MODULE_1__["ɵsetClassMetadata"](AppModule, [{
        type: _angular_core__WEBPACK_IMPORTED_MODULE_1__["NgModule"],
        args: [{
          declarations: [_app_component__WEBPACK_IMPORTED_MODULE_3__["AppComponent"], _ver_gen_ver_gen_component__WEBPACK_IMPORTED_MODULE_5__["VerGenComponent"], _ver_register_ver_register_component__WEBPACK_IMPORTED_MODULE_6__["RegisterDialog"], _app_component__WEBPACK_IMPORTED_MODULE_3__["NavrowComponent"], _ver_register_ver_register_component__WEBPACK_IMPORTED_MODULE_6__["VerRegisterComponent"], _progress_bar_progress_bar_component__WEBPACK_IMPORTED_MODULE_16__["ProgressBarComponent"]],
          imports: [_angular_platform_browser__WEBPACK_IMPORTED_MODULE_0__["BrowserModule"], _angular_platform_browser_animations__WEBPACK_IMPORTED_MODULE_4__["BrowserAnimationsModule"], _angular_common_http__WEBPACK_IMPORTED_MODULE_2__["HttpClientModule"], _angular_forms__WEBPACK_IMPORTED_MODULE_15__["FormsModule"], _angular_material_list__WEBPACK_IMPORTED_MODULE_7__["MatListModule"], _angular_material_expansion__WEBPACK_IMPORTED_MODULE_8__["MatExpansionModule"], _angular_material_dialog__WEBPACK_IMPORTED_MODULE_9__["MatDialogModule"], _angular_material_button__WEBPACK_IMPORTED_MODULE_10__["MatButtonModule"], _angular_material_input__WEBPACK_IMPORTED_MODULE_11__["MatInputModule"], _angular_material_select__WEBPACK_IMPORTED_MODULE_12__["MatSelectModule"], _angular_material_grid_list__WEBPACK_IMPORTED_MODULE_13__["MatGridListModule"], _angular_material_toolbar__WEBPACK_IMPORTED_MODULE_14__["MatToolbarModule"]],
          providers: [],
          bootstrap: [_app_component__WEBPACK_IMPORTED_MODULE_3__["AppComponent"]]
        }]
      }], null, null);
    })();
    /***/

  },

  /***/
  "./src/app/channel.service.ts":
  /*!************************************!*\
    !*** ./src/app/channel.service.ts ***!
    \************************************/

  /*! exports provided: ChannelService */

  /***/
  function srcAppChannelServiceTs(module, __webpack_exports__, __webpack_require__) {
    "use strict";

    __webpack_require__.r(__webpack_exports__);
    /* harmony export (binding) */


    __webpack_require__.d(__webpack_exports__, "ChannelService", function () {
      return ChannelService;
    });
    /* harmony import */


    var _angular_core__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(
    /*! @angular/core */
    "./node_modules/@angular/core/__ivy_ngcc__/fesm2015/core.js");
    /* harmony import */


    var rxjs_webSocket__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(
    /*! rxjs/webSocket */
    "./node_modules/rxjs/_esm2015/webSocket/index.js");

    var ChannelService = /*#__PURE__*/function () {
      function ChannelService() {
        _classCallCheck(this, ChannelService);

        this.channels = {};
      }

      _createClass(ChannelService, [{
        key: "create",
        value: function create(url) {
          var channel;

          if (typeof this.channels[url] == 'undefined') {
            // New channel
            channel = Object(rxjs_webSocket__WEBPACK_IMPORTED_MODULE_1__["webSocket"])(url);
            this.channels[url] = channel;
          } else {
            // Exist channel
            channel = this.channels[url];
          }

          return channel;
        }
      }, {
        key: "close",
        value: function close(url) {
          if (typeof this.channels[url] != 'undefined') {
            this.channels[url].complete();
          }
        }
      }]);

      return ChannelService;
    }();

    ChannelService.ɵfac = function ChannelService_Factory(t) {
      return new (t || ChannelService)();
    };

    ChannelService.ɵprov = _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵdefineInjectable"]({
      token: ChannelService,
      factory: ChannelService.ɵfac,
      providedIn: 'root'
    });
    /*@__PURE__*/

    (function () {
      _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵsetClassMetadata"](ChannelService, [{
        type: _angular_core__WEBPACK_IMPORTED_MODULE_0__["Injectable"],
        args: [{
          providedIn: 'root'
        }]
      }], function () {
        return [];
      }, null);
    })();
    /***/

  },

  /***/
  "./src/app/message.service.ts":
  /*!************************************!*\
    !*** ./src/app/message.service.ts ***!
    \************************************/

  /*! exports provided: MessageService */

  /***/
  function srcAppMessageServiceTs(module, __webpack_exports__, __webpack_require__) {
    "use strict";

    __webpack_require__.r(__webpack_exports__);
    /* harmony export (binding) */


    __webpack_require__.d(__webpack_exports__, "MessageService", function () {
      return MessageService;
    });
    /* harmony import */


    var _angular_core__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(
    /*! @angular/core */
    "./node_modules/@angular/core/__ivy_ngcc__/fesm2015/core.js");
    /* harmony import */


    var rxjs__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(
    /*! rxjs */
    "./node_modules/rxjs/_esm2015/index.js");
    /* harmony import */


    var _message__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(
    /*! ./message */
    "./src/app/message.ts");
    /* harmony import */


    var _channel_service__WEBPACK_IMPORTED_MODULE_3__ = __webpack_require__(
    /*! ./channel.service */
    "./src/app/channel.service.ts");

    var MessageQueue = /*#__PURE__*/function () {
      function MessageQueue() {
        _classCallCheck(this, MessageQueue);

        this.data = [];
      }

      _createClass(MessageQueue, [{
        key: "len",
        value: function len() {
          return this.data.length;
        }
      }, {
        key: "isFull",
        value: function isFull() {
          return this.len() > 0;
        }
      }, {
        key: "isEmpty",
        value: function isEmpty() {
          return this.len() == 0;
        }
      }, {
        key: "push",
        value: function push(msg) {
          this.data.push(msg);
        }
      }, {
        key: "pop",
        value: function pop() {
          return this.data.pop();
        }
      }]);

      return MessageQueue;
    }();

    var MessageService = /*#__PURE__*/function () {
      function MessageService(sock) {
        var _this = this;

        _classCallCheck(this, MessageService);

        this.sock_url = "ws://localhost:8000/commu/";
        this.socket = null;
        /**
         * With Help of msg_queues MessageService able to
         * provide messages that from server, to another
         * components or services.
         *
         *  ---- message ---> MessageService ---> queue ---> component
         */

        this.msg_queues = {};
        sock.create(this.sock_url).subscribe(function (msg) {
          if (Object(_message__WEBPACK_IMPORTED_MODULE_2__["message_check"])(msg) === false) {
            // invalid message
            return;
          }

          var message = {
            "type": msg["type"],
            "content": msg["content"]
          };
          var msg_type = message.type; // If type of thie message is subscribe then add it to
          // correspond queue.

          if (typeof _this.msg_queues[msg_type] != 'undefined') {
            _this.msg_queues[message.type].push(message);
          }
        }, function (err) {
          console.log(err);
        }, function () {
          console.log("complete");
        });
      }

      _createClass(MessageService, [{
        key: "register",
        value: function register(msg_type) {
          var _this2 = this;

          // To check that is this msg_type is unique.
          if (typeof this.msg_queues[msg_type] == "undefined") this.msg_queues[msg_type] = new MessageQueue();else return null;
          return new rxjs__WEBPACK_IMPORTED_MODULE_1__["Observable"](function (msg_receiver) {
            setInterval(function () {
              var q = _this2.msg_queues[msg_type];

              while (!q.isEmpty()) {
                msg_receiver.next(q.pop());
              }
            }, 3000);
          });
        }
      }]);

      return MessageService;
    }();

    MessageService.ɵfac = function MessageService_Factory(t) {
      return new (t || MessageService)(_angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵinject"](_channel_service__WEBPACK_IMPORTED_MODULE_3__["ChannelService"]));
    };

    MessageService.ɵprov = _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵdefineInjectable"]({
      token: MessageService,
      factory: MessageService.ɵfac,
      providedIn: 'root'
    });
    /*@__PURE__*/

    (function () {
      _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵsetClassMetadata"](MessageService, [{
        type: _angular_core__WEBPACK_IMPORTED_MODULE_0__["Injectable"],
        args: [{
          providedIn: 'root'
        }]
      }], function () {
        return [{
          type: _channel_service__WEBPACK_IMPORTED_MODULE_3__["ChannelService"]
        }];
      }, null);
    })();
    /***/

  },

  /***/
  "./src/app/message.ts":
  /*!****************************!*\
    !*** ./src/app/message.ts ***!
    \****************************/

  /*! exports provided: message_check */

  /***/
  function srcAppMessageTs(module, __webpack_exports__, __webpack_require__) {
    "use strict";

    __webpack_require__.r(__webpack_exports__);
    /* harmony export (binding) */


    __webpack_require__.d(__webpack_exports__, "message_check", function () {
      return message_check;
    });

    function message_check(msg) {
      if (typeof msg == 'object') {
        if (typeof msg['type'] != 'undefined' || typeof msg['content'] != 'undefined') {
          return true;
        }

        return false;
      }
    }
    /***/

  },

  /***/
  "./src/app/progress-bar/progress-bar.component.ts":
  /*!********************************************************!*\
    !*** ./src/app/progress-bar/progress-bar.component.ts ***!
    \********************************************************/

  /*! exports provided: ProgressBarComponent */

  /***/
  function srcAppProgressBarProgressBarComponentTs(module, __webpack_exports__, __webpack_require__) {
    "use strict";

    __webpack_require__.r(__webpack_exports__);
    /* harmony export (binding) */


    __webpack_require__.d(__webpack_exports__, "ProgressBarComponent", function () {
      return ProgressBarComponent;
    });
    /* harmony import */


    var _angular_core__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(
    /*! @angular/core */
    "./node_modules/@angular/core/__ivy_ngcc__/fesm2015/core.js");
    /* harmony import */


    var _message_service__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(
    /*! ../message.service */
    "./src/app/message.service.ts");

    var ProgressBarComponent = /*#__PURE__*/function () {
      function ProgressBarComponent(msg_service) {
        var _this3 = this;

        _classCallCheck(this, ProgressBarComponent);

        this.jobs = {};
        msg_service.register("JobMsg").subscribe(function (msg) {
          _this3.job_state_message_handle(msg);
        });
      }

      _createClass(ProgressBarComponent, [{
        key: "ngOnInit",
        value: function ngOnInit() {}
      }, {
        key: "job_state_message_handle",
        value: function job_state_message_handle(msg) {
          var content = msg.content;
          var subtype; // Corrupted by invalid format of message is
          // not allowed.

          try {
            subtype = content['subtype'];

            switch (subtype) {
              case "change":
                this.job_state_message_change_handle(msg);
                break;

              case "fin":
                this.job_state_message_fin_handle(msg);
                break;

              case "fail":
                this.job_state_message_fail_handle(msg);
                break;

              case "info":
                this.job_state_message_info_handle(msg);
                break;
            }
          } catch (error) {
            console.log(error);
          }
        }
      }, {
        key: "job_state_message_info_handle",
        value: function job_state_message_info_handle(msg) {
          var content = msg['content']['message']; // Create jobs from info in message.

          for (var jobid in content) {
            var job = {
              "jobid": jobid,
              tasks: content[jobid]
            };
            this.jobs[jobid] = job;
          }
        }
      }, {
        key: "job_state_message_change_handle",
        value: function job_state_message_change_handle(msg) {
          var content = msg['content']['message'];
          var jobid = content['jobid'];
          var taskid = content['taskid'];
          var state = content['state'];
          this.jobs[jobid].tasks[taskid].state = state;
        }
      }, {
        key: "job_state_message_fin_handle",
        value: function job_state_message_fin_handle(msg) {
          var content = msg['content']['message'];
          var jobid = content['jobid'];
          delete this.jobs[jobid];
        }
      }, {
        key: "job_state_message_fail_handle",
        value: function job_state_message_fail_handle(msg) {
          var content = msg['content']['message'];
          var jobid = content['jobid'];
          delete this.jobs[jobid];
        }
      }]);

      return ProgressBarComponent;
    }();

    ProgressBarComponent.ɵfac = function ProgressBarComponent_Factory(t) {
      return new (t || ProgressBarComponent)(_angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵdirectiveInject"](_message_service__WEBPACK_IMPORTED_MODULE_1__["MessageService"]));
    };

    ProgressBarComponent.ɵcmp = _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵdefineComponent"]({
      type: ProgressBarComponent,
      selectors: [["app-progress-bar"]],
      decls: 5,
      vars: 1,
      consts: [["id", "ProgressBar", 1, "mat-elevation-z5"]],
      template: function ProgressBarComponent_Template(rf, ctx) {
        if (rf & 1) {
          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementStart"](0, "div", 0);

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementStart"](1, "h3");

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵtext"](2, "ProgressBar");

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementEnd"]();

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementStart"](3, "p");

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵtext"](4);

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementEnd"]();

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementEnd"]();
        }

        if (rf & 2) {
          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵadvance"](4);

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵtextInterpolate"](ctx.jobs);
        }
      },
      styles: ["\n/*# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJzb3VyY2VzIjpbXSwibmFtZXMiOltdLCJtYXBwaW5ncyI6IiIsImZpbGUiOiJzcmMvYXBwL3Byb2dyZXNzLWJhci9wcm9ncmVzcy1iYXIuY29tcG9uZW50LmNzcyJ9 */"]
    });
    /*@__PURE__*/

    (function () {
      _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵsetClassMetadata"](ProgressBarComponent, [{
        type: _angular_core__WEBPACK_IMPORTED_MODULE_0__["Component"],
        args: [{
          selector: 'app-progress-bar',
          templateUrl: './progress-bar.component.html',
          styleUrls: ['./progress-bar.component.css']
        }]
      }], function () {
        return [{
          type: _message_service__WEBPACK_IMPORTED_MODULE_1__["MessageService"]
        }];
      }, null);
    })();
    /***/

  },

  /***/
  "./src/app/revision.service.ts":
  /*!*************************************!*\
    !*** ./src/app/revision.service.ts ***!
    \*************************************/

  /*! exports provided: RevisionService */

  /***/
  function srcAppRevisionServiceTs(module, __webpack_exports__, __webpack_require__) {
    "use strict";

    __webpack_require__.r(__webpack_exports__);
    /* harmony export (binding) */


    __webpack_require__.d(__webpack_exports__, "RevisionService", function () {
      return RevisionService;
    });
    /* harmony import */


    var _angular_core__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(
    /*! @angular/core */
    "./node_modules/@angular/core/__ivy_ngcc__/fesm2015/core.js");
    /* harmony import */


    var _angular_common_http__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(
    /*! @angular/common/http */
    "./node_modules/@angular/common/__ivy_ngcc__/fesm2015/http.js");

    var RevisionService = /*#__PURE__*/function () {
      function RevisionService(http) {
        _classCallCheck(this, RevisionService);

        this.http = http;
        this.revUrl = 'manager/api/revisions';
      }

      _createClass(RevisionService, [{
        key: "getRevision",
        value: function getRevision(sn) {
          var url = "".concat(this.revUrl, "/").concat(sn);
          return this.http.get(url);
        }
      }, {
        key: "getRevisions",
        value: function getRevisions() {
          return this.http.get(this.revUrl);
        }
      }, {
        key: "getSomeRevs",
        value: function getSomeRevs(sn, num) {
          var url = sn != null ? "".concat(this.revUrl, "/").concat(sn, "/getSomeRevsFrom") : "".concat(this.revUrl, "/getSomeRevs");
          var options = {
            params: {
              num: "".concat(num)
            }
          };
          return this.http.get(url, options);
        }
      }]);

      return RevisionService;
    }();

    RevisionService.ɵfac = function RevisionService_Factory(t) {
      return new (t || RevisionService)(_angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵinject"](_angular_common_http__WEBPACK_IMPORTED_MODULE_1__["HttpClient"]));
    };

    RevisionService.ɵprov = _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵdefineInjectable"]({
      token: RevisionService,
      factory: RevisionService.ɵfac,
      providedIn: 'root'
    });
    /*@__PURE__*/

    (function () {
      _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵsetClassMetadata"](RevisionService, [{
        type: _angular_core__WEBPACK_IMPORTED_MODULE_0__["Injectable"],
        args: [{
          providedIn: 'root'
        }]
      }], function () {
        return [{
          type: _angular_common_http__WEBPACK_IMPORTED_MODULE_1__["HttpClient"]
        }];
      }, null);
    })();
    /***/

  },

  /***/
  "./src/app/ver-gen/ver-gen.component.ts":
  /*!**********************************************!*\
    !*** ./src/app/ver-gen/ver-gen.component.ts ***!
    \**********************************************/

  /*! exports provided: VerGenComponent */

  /***/
  function srcAppVerGenVerGenComponentTs(module, __webpack_exports__, __webpack_require__) {
    "use strict";

    __webpack_require__.r(__webpack_exports__);
    /* harmony export (binding) */


    __webpack_require__.d(__webpack_exports__, "VerGenComponent", function () {
      return VerGenComponent;
    });
    /* harmony import */


    var _angular_core__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(
    /*! @angular/core */
    "./node_modules/@angular/core/__ivy_ngcc__/fesm2015/core.js");
    /* harmony import */


    var _version_service__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(
    /*! ../version.service */
    "./src/app/version.service.ts");
    /* harmony import */


    var _revision_service__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(
    /*! ../revision.service */
    "./src/app/revision.service.ts");
    /* harmony import */


    var _angular_material_list__WEBPACK_IMPORTED_MODULE_3__ = __webpack_require__(
    /*! @angular/material/list */
    "./node_modules/@angular/material/__ivy_ngcc__/fesm2015/list.js");
    /* harmony import */


    var _angular_material_form_field__WEBPACK_IMPORTED_MODULE_4__ = __webpack_require__(
    /*! @angular/material/form-field */
    "./node_modules/@angular/material/__ivy_ngcc__/fesm2015/form-field.js");
    /* harmony import */


    var _angular_material_select__WEBPACK_IMPORTED_MODULE_5__ = __webpack_require__(
    /*! @angular/material/select */
    "./node_modules/@angular/material/__ivy_ngcc__/fesm2015/select.js");
    /* harmony import */


    var _angular_common__WEBPACK_IMPORTED_MODULE_6__ = __webpack_require__(
    /*! @angular/common */
    "./node_modules/@angular/common/__ivy_ngcc__/fesm2015/common.js");
    /* harmony import */


    var _angular_material_button__WEBPACK_IMPORTED_MODULE_7__ = __webpack_require__(
    /*! @angular/material/button */
    "./node_modules/@angular/material/__ivy_ngcc__/fesm2015/button.js");
    /* harmony import */


    var _angular_material_core__WEBPACK_IMPORTED_MODULE_8__ = __webpack_require__(
    /*! @angular/material/core */
    "./node_modules/@angular/material/__ivy_ngcc__/fesm2015/core.js");

    function VerGenComponent_mat_option_10_Template(rf, ctx) {
      if (rf & 1) {
        _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementStart"](0, "mat-option", 6);

        _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵtext"](1);

        _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementEnd"]();
      }

      if (rf & 2) {
        var version_r6 = ctx.$implicit;

        _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵproperty"]("value", version_r6);

        _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵadvance"](1);

        _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵtextInterpolate1"](" ", version_r6.vsn, " ");
      }
    }

    function VerGenComponent_mat_option_17_Template(rf, ctx) {
      if (rf & 1) {
        _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementStart"](0, "mat-option", 6);

        _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵtext"](1);

        _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementEnd"]();
      }

      if (rf & 2) {
        var revision_r7 = ctx.$implicit;

        _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵproperty"]("value", revision_r7.sn);

        _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵadvance"](1);

        _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵtextInterpolate1"](" ", revision_r7.sn, " ");
      }
    }

    function VerGenComponent_mat_option_24_Template(rf, ctx) {
      if (rf & 1) {
        _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementStart"](0, "mat-option", 6);

        _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵtext"](1);

        _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementEnd"]();
      }

      if (rf & 2) {
        var revision_r8 = ctx.$implicit;

        _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵproperty"]("value", revision_r8.sn);

        _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵadvance"](1);

        _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵtextInterpolate1"](" ", revision_r8.sn, " ");
      }
    }

    var VerGenComponent = /*#__PURE__*/function () {
      function VerGenComponent(verService, revService) {
        _classCallCheck(this, VerGenComponent);

        this.verService = verService;
        this.revService = revService;
        this.versions = [];
        this.revisions = [];
      }

      _createClass(VerGenComponent, [{
        key: "ngOnInit",
        value: function ngOnInit() {
          var _this4 = this;

          this.verService.getVersions().subscribe(function (versions) {
            return _this4.versions = versions;
          });
          this.revService.getRevisions().subscribe(function (revisions) {
            return _this4.revisions = revisions;
          });
        }
      }, {
        key: "generate",
        value: function generate(version) {
          var buildInfo = {};

          if (typeof version !== 'undefined') {
            if ((arguments.length <= 1 ? 0 : arguments.length - 1) === 2) {
              buildInfo = {
                logFrom: arguments.length <= 1 ? undefined : arguments[1],
                logTo: arguments.length <= 2 ? undefined : arguments[2]
              };
            }

            var build = {
              ver: version,
              info: buildInfo
            };
            this.verService.generate(build).subscribe();
          }
        }
      }]);

      return VerGenComponent;
    }();

    VerGenComponent.ɵfac = function VerGenComponent_Factory(t) {
      return new (t || VerGenComponent)(_angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵdirectiveInject"](_version_service__WEBPACK_IMPORTED_MODULE_1__["VersionService"]), _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵdirectiveInject"](_revision_service__WEBPACK_IMPORTED_MODULE_2__["RevisionService"]));
    };

    VerGenComponent.ɵcmp = _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵdefineComponent"]({
      type: VerGenComponent,
      selectors: [["app-ver-gen"]],
      decls: 28,
      vars: 3,
      consts: [["id", "VerGenPanel", 1, "mat-elevation-z5"], ["SelectedVersion", ""], [3, "value", 4, "ngFor", "ngForOf"], ["logFrom", ""], ["logTo", ""], ["id", "genButton", "mat-flat-button", "", "color", "primary", 3, "click"], [3, "value"]],
      template: function VerGenComponent_Template(rf, ctx) {
        if (rf & 1) {
          var _r9 = _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵgetCurrentView"]();

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementStart"](0, "div", 0);

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementStart"](1, "h3");

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵtext"](2, "Version Generate");

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementEnd"]();

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementStart"](3, "mat-list");

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementStart"](4, "mat-list-item");

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementStart"](5, "mat-form-field");

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementStart"](6, "mat-label");

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵtext"](7, "Version");

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementEnd"]();

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementStart"](8, "mat-select", null, 1);

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵtemplate"](10, VerGenComponent_mat_option_10_Template, 2, 2, "mat-option", 2);

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementEnd"]();

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementEnd"]();

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementEnd"]();

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementStart"](11, "mat-list-item");

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementStart"](12, "mat-form-field");

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementStart"](13, "mat-label");

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵtext"](14, "Log from");

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementEnd"]();

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementStart"](15, "mat-select", null, 3);

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵtemplate"](17, VerGenComponent_mat_option_17_Template, 2, 2, "mat-option", 2);

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementEnd"]();

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementEnd"]();

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementEnd"]();

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementStart"](18, "mat-list-item");

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementStart"](19, "mat-form-field");

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementStart"](20, "mat-label");

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵtext"](21, "Log from");

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementEnd"]();

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementStart"](22, "mat-select", null, 4);

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵtemplate"](24, VerGenComponent_mat_option_24_Template, 2, 2, "mat-option", 2);

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementEnd"]();

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementEnd"]();

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementEnd"]();

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementStart"](25, "mat-list-item");

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementStart"](26, "button", 5);

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵlistener"]("click", function VerGenComponent_Template_button_click_26_listener() {
            _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵrestoreView"](_r9);

            var _r0 = _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵreference"](9);

            var _r2 = _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵreference"](16);

            var _r4 = _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵreference"](23);

            return ctx.generate(_r0.value, _r2.value, _r4.value);
          });

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵtext"](27, " Generate ");

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementEnd"]();

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementEnd"]();

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementEnd"]();

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementEnd"]();
        }

        if (rf & 2) {
          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵadvance"](10);

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵproperty"]("ngForOf", ctx.versions);

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵadvance"](7);

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵproperty"]("ngForOf", ctx.revisions);

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵadvance"](7);

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵproperty"]("ngForOf", ctx.revisions);
        }
      },
      directives: [_angular_material_list__WEBPACK_IMPORTED_MODULE_3__["MatList"], _angular_material_list__WEBPACK_IMPORTED_MODULE_3__["MatListItem"], _angular_material_form_field__WEBPACK_IMPORTED_MODULE_4__["MatFormField"], _angular_material_form_field__WEBPACK_IMPORTED_MODULE_4__["MatLabel"], _angular_material_select__WEBPACK_IMPORTED_MODULE_5__["MatSelect"], _angular_common__WEBPACK_IMPORTED_MODULE_6__["NgForOf"], _angular_material_button__WEBPACK_IMPORTED_MODULE_7__["MatButton"], _angular_material_core__WEBPACK_IMPORTED_MODULE_8__["MatOption"]],
      styles: ["#VerGenPanel[_ngcontent-%COMP%] {\n    border-style: none;\n    border-width: 3px;\n    padding: 10px;\n    border-radius: 4px;\n}\n/*# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJzb3VyY2VzIjpbInNyYy9hcHAvdmVyLWdlbi92ZXItZ2VuLmNvbXBvbmVudC5jc3MiXSwibmFtZXMiOltdLCJtYXBwaW5ncyI6IkFBQUE7SUFDSSxrQkFBa0I7SUFDbEIsaUJBQWlCO0lBQ2pCLGFBQWE7SUFDYixrQkFBa0I7QUFDdEIiLCJmaWxlIjoic3JjL2FwcC92ZXItZ2VuL3Zlci1nZW4uY29tcG9uZW50LmNzcyIsInNvdXJjZXNDb250ZW50IjpbIiNWZXJHZW5QYW5lbCB7XG4gICAgYm9yZGVyLXN0eWxlOiBub25lO1xuICAgIGJvcmRlci13aWR0aDogM3B4O1xuICAgIHBhZGRpbmc6IDEwcHg7XG4gICAgYm9yZGVyLXJhZGl1czogNHB4O1xufVxuIl19 */"]
    });
    /*@__PURE__*/

    (function () {
      _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵsetClassMetadata"](VerGenComponent, [{
        type: _angular_core__WEBPACK_IMPORTED_MODULE_0__["Component"],
        args: [{
          selector: 'app-ver-gen',
          templateUrl: './ver-gen.component.html',
          styleUrls: ['./ver-gen.component.css']
        }]
      }], function () {
        return [{
          type: _version_service__WEBPACK_IMPORTED_MODULE_1__["VersionService"]
        }, {
          type: _revision_service__WEBPACK_IMPORTED_MODULE_2__["RevisionService"]
        }];
      }, null);
    })();
    /***/

  },

  /***/
  "./src/app/ver-register/ver-register.component.ts":
  /*!********************************************************!*\
    !*** ./src/app/ver-register/ver-register.component.ts ***!
    \********************************************************/

  /*! exports provided: VerRegisterComponent, RegisterDialog */

  /***/
  function srcAppVerRegisterVerRegisterComponentTs(module, __webpack_exports__, __webpack_require__) {
    "use strict";

    __webpack_require__.r(__webpack_exports__);
    /* harmony export (binding) */


    __webpack_require__.d(__webpack_exports__, "VerRegisterComponent", function () {
      return VerRegisterComponent;
    });
    /* harmony export (binding) */


    __webpack_require__.d(__webpack_exports__, "RegisterDialog", function () {
      return RegisterDialog;
    });
    /* harmony import */


    var _angular_core__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(
    /*! @angular/core */
    "./node_modules/@angular/core/__ivy_ngcc__/fesm2015/core.js");
    /* harmony import */


    var _version_service__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(
    /*! ../version.service */
    "./src/app/version.service.ts");
    /* harmony import */


    var _revision_service__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(
    /*! ../revision.service */
    "./src/app/revision.service.ts");
    /* harmony import */


    var _angular_material_dialog__WEBPACK_IMPORTED_MODULE_3__ = __webpack_require__(
    /*! @angular/material/dialog */
    "./node_modules/@angular/material/__ivy_ngcc__/fesm2015/dialog.js");
    /* harmony import */


    var _angular_material_list__WEBPACK_IMPORTED_MODULE_4__ = __webpack_require__(
    /*! @angular/material/list */
    "./node_modules/@angular/material/__ivy_ngcc__/fesm2015/list.js");
    /* harmony import */


    var _angular_common__WEBPACK_IMPORTED_MODULE_5__ = __webpack_require__(
    /*! @angular/common */
    "./node_modules/@angular/common/__ivy_ngcc__/fesm2015/common.js");
    /* harmony import */


    var _angular_material_form_field__WEBPACK_IMPORTED_MODULE_6__ = __webpack_require__(
    /*! @angular/material/form-field */
    "./node_modules/@angular/material/__ivy_ngcc__/fesm2015/form-field.js");
    /* harmony import */


    var _angular_material_input__WEBPACK_IMPORTED_MODULE_7__ = __webpack_require__(
    /*! @angular/material/input */
    "./node_modules/@angular/material/__ivy_ngcc__/fesm2015/input.js");
    /* harmony import */


    var _angular_forms__WEBPACK_IMPORTED_MODULE_8__ = __webpack_require__(
    /*! @angular/forms */
    "./node_modules/@angular/forms/__ivy_ngcc__/fesm2015/forms.js");
    /* harmony import */


    var _angular_material_button__WEBPACK_IMPORTED_MODULE_9__ = __webpack_require__(
    /*! @angular/material/button */
    "./node_modules/@angular/material/__ivy_ngcc__/fesm2015/button.js");

    function VerRegisterComponent_mat_list_4_Template(rf, ctx) {
      if (rf & 1) {
        var _r3 = _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵgetCurrentView"]();

        _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementStart"](0, "mat-list", 4);

        _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementStart"](1, "button", 5);

        _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵlistener"]("click", function VerRegisterComponent_mat_list_4_Template_button_click_1_listener() {
          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵrestoreView"](_r3);

          var revision_r1 = ctx.$implicit;

          var ctx_r2 = _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵnextContext"]();

          return ctx_r2.register(revision_r1.sn);
        });

        _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementStart"](2, "a");

        _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵtext"](3);

        _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵpipe"](4, "slice");

        _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementEnd"]();

        _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementEnd"]();

        _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementEnd"]();
      }

      if (rf & 2) {
        var revision_r1 = ctx.$implicit;

        _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵadvance"](3);

        _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵtextInterpolate"](_angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵpipeBind3"](4, 1, revision_r1.comment, 0, 40));
      }
    }

    var VerRegisterComponent = /*#__PURE__*/function () {
      function VerRegisterComponent(verService, revService, dialog) {
        _classCallCheck(this, VerRegisterComponent);

        this.verService = verService;
        this.revService = revService;
        this.dialog = dialog;
        this.versions = [];
        this.revisions = [];
        this.lastScrollTop = 0;
        this.revList = null;
      }

      _createClass(VerRegisterComponent, [{
        key: "ngOnInit",
        value: function ngOnInit() {
          this.getVersions();
          this.getSomeRevs(null, 20);
        }
      }, {
        key: "register",
        value: function register(rev) {
          var _this5 = this;

          var ref = this.dialog.open(RegisterDialog, {
            width: '250px'
          });
          ref.afterClosed().subscribe(function (result) {
            if (result !== undefined) {
              var ver = {
                vsn: result,
                sn: rev
              };

              _this5.verService.addVersion(ver).subscribe();
            }
          });
        }
      }, {
        key: "remove",
        value: function remove(ver) {
          this.verService.removeVersion(ver.vsn).subscribe();
        }
      }, {
        key: "getVersions",
        value: function getVersions() {
          var _this6 = this;

          this.verService.getVersions().subscribe(function (versions) {
            return _this6.versions = versions;
          });
        }
      }, {
        key: "getRevisions",
        value: function getRevisions() {
          var _this7 = this;

          this.revService.getRevisions().subscribe(function (revisions) {
            return _this7.revisions = revisions;
          });
        }
      }, {
        key: "getSomeRevs",
        value: function getSomeRevs(sn, num) {
          var _this8 = this;

          this.revService.getSomeRevs(sn, num).subscribe(function (revisions) {
            return _this8.revisions = _this8.revisions.concat(revisions);
          });
        }
      }, {
        key: "logging",
        value: function logging(msg) {
          console.log(msg);
        }
      }, {
        key: "onScroll",
        value: function onScroll(event) {
          var _this9 = this;

          // visible height + pixel scrolled >= total height
          if (event.target.offsetHeight + event.target.scrollTop >= event.target.scrollHeight) {
            var lastSn = this.revisions[this.revisions.length - 1];
            this.revService.getSomeRevs(lastSn.sn, 10).subscribe(function (revisions) {
              var height = event.target.scrollHeight;
              _this9.revisions = _this9.revisions.concat(revisions);
            });
          }
        }
      }]);

      return VerRegisterComponent;
    }();

    VerRegisterComponent.ɵfac = function VerRegisterComponent_Factory(t) {
      return new (t || VerRegisterComponent)(_angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵdirectiveInject"](_version_service__WEBPACK_IMPORTED_MODULE_1__["VersionService"]), _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵdirectiveInject"](_revision_service__WEBPACK_IMPORTED_MODULE_2__["RevisionService"]), _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵdirectiveInject"](_angular_material_dialog__WEBPACK_IMPORTED_MODULE_3__["MatDialog"]));
    };

    VerRegisterComponent.ɵcmp = _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵdefineComponent"]({
      type: VerRegisterComponent,
      selectors: [["app-ver-register"]],
      decls: 5,
      vars: 1,
      consts: [["id", "RegPanel", 1, "mat-elevation-z5"], [1, "registerTitle"], ["id", "revList", 3, "scroll"], ["class", "mat-elevation-z2", 4, "ngFor", "ngForOf"], [1, "mat-elevation-z2"], [1, "revButton", 3, "click"]],
      template: function VerRegisterComponent_Template(rf, ctx) {
        if (rf & 1) {
          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementStart"](0, "div", 0);

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementStart"](1, "h3", 1);

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵtext"](2, "Version Register");

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementEnd"]();

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementStart"](3, "mat-action-list", 2);

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵlistener"]("scroll", function VerRegisterComponent_Template_mat_action_list_scroll_3_listener($event) {
            return ctx.onScroll($event);
          });

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵtemplate"](4, VerRegisterComponent_mat_list_4_Template, 5, 5, "mat-list", 3);

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementEnd"]();

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementEnd"]();
        }

        if (rf & 2) {
          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵadvance"](4);

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵproperty"]("ngForOf", ctx.revisions);
        }
      },
      directives: [_angular_material_list__WEBPACK_IMPORTED_MODULE_4__["MatList"], _angular_common__WEBPACK_IMPORTED_MODULE_5__["NgForOf"]],
      pipes: [_angular_common__WEBPACK_IMPORTED_MODULE_5__["SlicePipe"]],
      styles: ["#RegPanel[_ngcontent-%COMP%] {\n    border-style: none;\n    border-width: 3px;\n    padding: 20px 15px 15px 15px;\n    border-radius: 4px;\n}\n\nmat-action-list[_ngcontent-%COMP%] {\n    margin: 0 0 2em 0;\n    list-style-type: none;\n    padding: 0;\n    width: 38em;\n    max-height: 35em;\n    overflow: auto;\n}\n\n#revList[_ngcontent-%COMP%]   mat-list[_ngcontent-%COMP%] {\n    position: relative;\n    cursor: pointer;\n    background-color: #EEE;\n    margin: .5em;\n    padding: .3em 0;\n    height: 1.6em;\n    border-radius: 4px;\n    min-width: 35em;\n}\n\n#revList[_ngcontent-%COMP%]   mat-list[_ngcontent-%COMP%]:hover {\n    color: #607D8B;\n    left: .1em;\n}\n\nbutton[_ngcontent-%COMP%] {\n  background-color: #eee;\n  border: none;\n  font-family: Arial;\n  height: 1.6em;\n  width: 100%;\n  border-radisu: 4px;\n}\n/*# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJzb3VyY2VzIjpbInNyYy9hcHAvdmVyLXJlZ2lzdGVyL3Zlci1yZWdpc3Rlci5jb21wb25lbnQuY3NzIl0sIm5hbWVzIjpbXSwibWFwcGluZ3MiOiJBQUFBO0lBQ0ksa0JBQWtCO0lBQ2xCLGlCQUFpQjtJQUNqQiw0QkFBNEI7SUFDNUIsa0JBQWtCO0FBQ3RCOztBQUVBO0lBQ0ksaUJBQWlCO0lBQ2pCLHFCQUFxQjtJQUNyQixVQUFVO0lBQ1YsV0FBVztJQUNYLGdCQUFnQjtJQUNoQixjQUFjO0FBQ2xCOztBQUVBO0lBQ0ksa0JBQWtCO0lBQ2xCLGVBQWU7SUFDZixzQkFBc0I7SUFDdEIsWUFBWTtJQUNaLGVBQWU7SUFDZixhQUFhO0lBQ2Isa0JBQWtCO0lBQ2xCLGVBQWU7QUFDbkI7O0FBRUE7SUFDSSxjQUFjO0lBQ2QsVUFBVTtBQUNkOztBQUVBO0VBQ0Usc0JBQXNCO0VBQ3RCLFlBQVk7RUFDWixrQkFBa0I7RUFDbEIsYUFBYTtFQUNiLFdBQVc7RUFDWCxrQkFBa0I7QUFDcEIiLCJmaWxlIjoic3JjL2FwcC92ZXItcmVnaXN0ZXIvdmVyLXJlZ2lzdGVyLmNvbXBvbmVudC5jc3MiLCJzb3VyY2VzQ29udGVudCI6WyIjUmVnUGFuZWwge1xuICAgIGJvcmRlci1zdHlsZTogbm9uZTtcbiAgICBib3JkZXItd2lkdGg6IDNweDtcbiAgICBwYWRkaW5nOiAyMHB4IDE1cHggMTVweCAxNXB4O1xuICAgIGJvcmRlci1yYWRpdXM6IDRweDtcbn1cblxubWF0LWFjdGlvbi1saXN0IHtcbiAgICBtYXJnaW46IDAgMCAyZW0gMDtcbiAgICBsaXN0LXN0eWxlLXR5cGU6IG5vbmU7XG4gICAgcGFkZGluZzogMDtcbiAgICB3aWR0aDogMzhlbTtcbiAgICBtYXgtaGVpZ2h0OiAzNWVtO1xuICAgIG92ZXJmbG93OiBhdXRvO1xufVxuXG4jcmV2TGlzdCBtYXQtbGlzdCB7XG4gICAgcG9zaXRpb246IHJlbGF0aXZlO1xuICAgIGN1cnNvcjogcG9pbnRlcjtcbiAgICBiYWNrZ3JvdW5kLWNvbG9yOiAjRUVFO1xuICAgIG1hcmdpbjogLjVlbTtcbiAgICBwYWRkaW5nOiAuM2VtIDA7XG4gICAgaGVpZ2h0OiAxLjZlbTtcbiAgICBib3JkZXItcmFkaXVzOiA0cHg7XG4gICAgbWluLXdpZHRoOiAzNWVtO1xufVxuXG4jcmV2TGlzdCBtYXQtbGlzdDpob3ZlciB7XG4gICAgY29sb3I6ICM2MDdEOEI7XG4gICAgbGVmdDogLjFlbTtcbn1cblxuYnV0dG9uIHtcbiAgYmFja2dyb3VuZC1jb2xvcjogI2VlZTtcbiAgYm9yZGVyOiBub25lO1xuICBmb250LWZhbWlseTogQXJpYWw7XG4gIGhlaWdodDogMS42ZW07XG4gIHdpZHRoOiAxMDAlO1xuICBib3JkZXItcmFkaXN1OiA0cHg7XG59XG4iXX0= */"]
    });
    /*@__PURE__*/

    (function () {
      _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵsetClassMetadata"](VerRegisterComponent, [{
        type: _angular_core__WEBPACK_IMPORTED_MODULE_0__["Component"],
        args: [{
          selector: 'app-ver-register',
          templateUrl: './ver-register.component.html',
          styleUrls: ['./ver-register.component.css']
        }]
      }], function () {
        return [{
          type: _version_service__WEBPACK_IMPORTED_MODULE_1__["VersionService"]
        }, {
          type: _revision_service__WEBPACK_IMPORTED_MODULE_2__["RevisionService"]
        }, {
          type: _angular_material_dialog__WEBPACK_IMPORTED_MODULE_3__["MatDialog"]
        }];
      }, null);
    })();

    var RegisterDialog = /*#__PURE__*/function () {
      function RegisterDialog(dialogRef) {
        _classCallCheck(this, RegisterDialog);

        this.dialogRef = dialogRef;
      }

      _createClass(RegisterDialog, [{
        key: "onCancel",
        value: function onCancel() {
          this.dialogRef.close();
        }
      }]);

      return RegisterDialog;
    }();

    RegisterDialog.ɵfac = function RegisterDialog_Factory(t) {
      return new (t || RegisterDialog)(_angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵdirectiveInject"](_angular_material_dialog__WEBPACK_IMPORTED_MODULE_3__["MatDialogRef"]));
    };

    RegisterDialog.ɵcmp = _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵdefineComponent"]({
      type: RegisterDialog,
      selectors: [["register-dialog"]],
      decls: 12,
      vars: 2,
      consts: [["mat-dialog-title", ""], ["mat-dialog-content", ""], ["matInput", "", 3, "ngModel", "ngModelChange"], ["mat-dialog-actions", ""], ["mat-button", "", 3, "click"], ["mat-button", "", 3, "mat-dialog-close"]],
      template: function RegisterDialog_Template(rf, ctx) {
        if (rf & 1) {
          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementStart"](0, "h1", 0);

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵtext"](1, "Version Register");

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementEnd"]();

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementStart"](2, "div", 1);

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementStart"](3, "mat-form-field");

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementStart"](4, "p");

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵtext"](5, "Version Identity?");

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementEnd"]();

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementStart"](6, "input", 2);

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵlistener"]("ngModelChange", function RegisterDialog_Template_input_ngModelChange_6_listener($event) {
            return ctx.version = $event;
          });

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementEnd"]();

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementEnd"]();

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementEnd"]();

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementStart"](7, "div", 3);

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementStart"](8, "button", 4);

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵlistener"]("click", function RegisterDialog_Template_button_click_8_listener() {
            return ctx.onCancel();
          });

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵtext"](9, "No Thanks");

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementEnd"]();

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementStart"](10, "button", 5);

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵtext"](11, "Ok");

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementEnd"]();

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵelementEnd"]();
        }

        if (rf & 2) {
          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵadvance"](6);

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵproperty"]("ngModel", ctx.version);

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵadvance"](4);

          _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵproperty"]("mat-dialog-close", ctx.version);
        }
      },
      directives: [_angular_material_dialog__WEBPACK_IMPORTED_MODULE_3__["MatDialogTitle"], _angular_material_dialog__WEBPACK_IMPORTED_MODULE_3__["MatDialogContent"], _angular_material_form_field__WEBPACK_IMPORTED_MODULE_6__["MatFormField"], _angular_material_input__WEBPACK_IMPORTED_MODULE_7__["MatInput"], _angular_forms__WEBPACK_IMPORTED_MODULE_8__["DefaultValueAccessor"], _angular_forms__WEBPACK_IMPORTED_MODULE_8__["NgControlStatus"], _angular_forms__WEBPACK_IMPORTED_MODULE_8__["NgModel"], _angular_material_dialog__WEBPACK_IMPORTED_MODULE_3__["MatDialogActions"], _angular_material_button__WEBPACK_IMPORTED_MODULE_9__["MatButton"], _angular_material_dialog__WEBPACK_IMPORTED_MODULE_3__["MatDialogClose"]],
      encapsulation: 2
    });
    /*@__PURE__*/

    (function () {
      _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵsetClassMetadata"](RegisterDialog, [{
        type: _angular_core__WEBPACK_IMPORTED_MODULE_0__["Component"],
        args: [{
          selector: 'register-dialog',
          templateUrl: 'register-dialog.html'
        }]
      }], function () {
        return [{
          type: _angular_material_dialog__WEBPACK_IMPORTED_MODULE_3__["MatDialogRef"]
        }];
      }, null);
    })();
    /***/

  },

  /***/
  "./src/app/version.service.ts":
  /*!************************************!*\
    !*** ./src/app/version.service.ts ***!
    \************************************/

  /*! exports provided: VersionService */

  /***/
  function srcAppVersionServiceTs(module, __webpack_exports__, __webpack_require__) {
    "use strict";

    __webpack_require__.r(__webpack_exports__);
    /* harmony export (binding) */


    __webpack_require__.d(__webpack_exports__, "VersionService", function () {
      return VersionService;
    });
    /* harmony import */


    var _angular_core__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(
    /*! @angular/core */
    "./node_modules/@angular/core/__ivy_ngcc__/fesm2015/core.js");
    /* harmony import */


    var _angular_common_http__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(
    /*! @angular/common/http */
    "./node_modules/@angular/common/__ivy_ngcc__/fesm2015/http.js");

    var VersionService = /*#__PURE__*/function () {
      function VersionService(http) {
        _classCallCheck(this, VersionService);

        this.http = http;
        this.verUrl = 'manager/api/versions';
        this.httpOptions = {
          headers: new _angular_common_http__WEBPACK_IMPORTED_MODULE_1__["HttpHeaders"]({
            'Content-Type': 'application/json'
          })
        };
      }

      _createClass(VersionService, [{
        key: "getVersion",
        value: function getVersion(vsn) {
          var url = "".concat(this.verUrl, "/").concat(vsn, "/");
          return this.http.get(url);
        }
      }, {
        key: "getVersions",
        value: function getVersions() {
          return this.http.get("".concat(this.verUrl, "/"));
        }
      }, {
        key: "updateVersion",
        value: function updateVersion(ver) {
          return this.http.put("".concat(this.verUrl, "/"), ver, this.httpOptions);
        }
      }, {
        key: "removeVersion",
        value: function removeVersion(vsn) {
          var url = "".concat(this.verUrl, "/").concat(vsn, "/");
          return this.http["delete"](url, this.httpOptions);
        }
      }, {
        key: "addVersion",
        value: function addVersion(ver) {
          return this.http.post("".concat(this.verUrl, "/"), ver, this.httpOptions);
        }
      }, {
        key: "generate",
        value: function generate(build) {
          var genUrl = "".concat(this.verUrl, "/").concat(build.ver.vsn, "/generate/");
          return this.http.put(genUrl, build.info, this.httpOptions);
        }
      }]);

      return VersionService;
    }();

    VersionService.ɵfac = function VersionService_Factory(t) {
      return new (t || VersionService)(_angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵinject"](_angular_common_http__WEBPACK_IMPORTED_MODULE_1__["HttpClient"]));
    };

    VersionService.ɵprov = _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵɵdefineInjectable"]({
      token: VersionService,
      factory: VersionService.ɵfac,
      providedIn: 'root'
    });
    /*@__PURE__*/

    (function () {
      _angular_core__WEBPACK_IMPORTED_MODULE_0__["ɵsetClassMetadata"](VersionService, [{
        type: _angular_core__WEBPACK_IMPORTED_MODULE_0__["Injectable"],
        args: [{
          providedIn: 'root'
        }]
      }], function () {
        return [{
          type: _angular_common_http__WEBPACK_IMPORTED_MODULE_1__["HttpClient"]
        }];
      }, null);
    })();
    /***/

  },

  /***/
  "./src/environments/environment.ts":
  /*!*****************************************!*\
    !*** ./src/environments/environment.ts ***!
    \*****************************************/

  /*! exports provided: environment */

  /***/
  function srcEnvironmentsEnvironmentTs(module, __webpack_exports__, __webpack_require__) {
    "use strict";

    __webpack_require__.r(__webpack_exports__);
    /* harmony export (binding) */


    __webpack_require__.d(__webpack_exports__, "environment", function () {
      return environment;
    }); // This file can be replaced during build by using the `fileReplacements` array.
    // `ng build --prod` replaces `environment.ts` with `environment.prod.ts`.
    // The list of file replacements can be found in `angular.json`.


    var environment = {
      production: false
    };
    /*
     * For easier debugging in development mode, you can import the following file
     * to ignore zone related error stack frames such as `zone.run`, `zoneDelegate.invokeTask`.
     *
     * This import should be commented out in production mode because it will have a negative impact
     * on performance if an error is thrown.
     */
    // import 'zone.js/dist/zone-error';  // Included with Angular CLI.

    /***/
  },

  /***/
  "./src/main.ts":
  /*!*********************!*\
    !*** ./src/main.ts ***!
    \*********************/

  /*! no exports provided */

  /***/
  function srcMainTs(module, __webpack_exports__, __webpack_require__) {
    "use strict";

    __webpack_require__.r(__webpack_exports__);
    /* harmony import */


    var _angular_core__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(
    /*! @angular/core */
    "./node_modules/@angular/core/__ivy_ngcc__/fesm2015/core.js");
    /* harmony import */


    var _environments_environment__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(
    /*! ./environments/environment */
    "./src/environments/environment.ts");
    /* harmony import */


    var _app_app_module__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(
    /*! ./app/app.module */
    "./src/app/app.module.ts");
    /* harmony import */


    var _angular_platform_browser__WEBPACK_IMPORTED_MODULE_3__ = __webpack_require__(
    /*! @angular/platform-browser */
    "./node_modules/@angular/platform-browser/__ivy_ngcc__/fesm2015/platform-browser.js");

    if (_environments_environment__WEBPACK_IMPORTED_MODULE_1__["environment"].production) {
      Object(_angular_core__WEBPACK_IMPORTED_MODULE_0__["enableProdMode"])();
    }

    _angular_platform_browser__WEBPACK_IMPORTED_MODULE_3__["platformBrowser"]().bootstrapModule(_app_app_module__WEBPACK_IMPORTED_MODULE_2__["AppModule"])["catch"](function (err) {
      return console.error(err);
    });
    /***/

  },

  /***/
  0:
  /*!***************************!*\
    !*** multi ./src/main.ts ***!
    \***************************/

  /*! no static exports found */

  /***/
  function _(module, exports, __webpack_require__) {
    module.exports = __webpack_require__(
    /*! /home/ayden/Codebase/VerManager/manager/static/browser/src/main.ts */
    "./src/main.ts");
    /***/
  }
}, [[0, "runtime", "vendor"]]]);
//# sourceMappingURL=main-es5.js.map