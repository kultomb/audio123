def openwin():
    import os
    from pathlib import Path
    from PySide6 import QtWidgets
    from videotrans.configure.config import tr,params,settings,app_cfg
    from videotrans.util import tools
    from videotrans.util.TestSrtTrans import TestSrtTrans
    from videotrans import translator
    def feed(d):
        if not d.startswith("ok"):
            tools.show_error(d)
        else:
            QtWidgets.QMessageBox.information(winobj, "OK", d[3:])
        winobj.test.setText(tr("Test"))

    def test():
        key = winobj.gemini_key.text()
        model = winobj.model.currentText()
        gemini_maxtoken = winobj.gemini_maxtoken.text()
        params["gemini_maxtoken"] = gemini_maxtoken
        os.environ['GOOGLE_API_KEY'] = key
        params["gemini_model"] = model
        params["gemini_key"] = key

        # Vertex AI params
        auth_type = 'vertex' if winobj.radio_vertex.isChecked() else 'api_key'
        params["gemini_auth_type"] = auth_type
        params["gemini_vertex_json"] = winobj.vertex_json_path.text()
        params["gemini_vertex_project"] = winobj.vertex_project.text()
        params["gemini_vertex_location"] = winobj.vertex_location.text()

        # Prompt style
        style_map = {0: 'default', 1: 'tutorial', 2: 'review', 3: 'dialogue'}
        params["gemini_prompt_style"] = style_map.get(winobj.prompt_style.currentIndex(), 'default')

        ttsmodel = winobj.ttsmodel.currentText()
        params["gemini_ttsmodel"] = ttsmodel

        params.save()
        winobj.test.setText(tr("Testing..."))
        task = TestSrtTrans(parent=winobj, translator_type=translator.GEMINI_INDEX)
        task.uito.connect(feed)
        task.start()

    def save():
        key = winobj.gemini_key.text()
        model = winobj.model.currentText()

        
        gemini_maxtoken = winobj.gemini_maxtoken.text()
        params["gemini_maxtoken"] = gemini_maxtoken

        params["gemini_model"] = model
        params["gemini_key"] = key

        # Vertex AI params
        auth_type = 'vertex' if winobj.radio_vertex.isChecked() else 'api_key'
        params["gemini_auth_type"] = auth_type
        params["gemini_vertex_json"] = winobj.vertex_json_path.text()
        params["gemini_vertex_project"] = winobj.vertex_project.text()
        params["gemini_vertex_location"] = winobj.vertex_location.text()

        # Prompt style
        style_map = {0: 'default', 1: 'tutorial', 2: 'review', 3: 'dialogue'}
        params["gemini_prompt_style"] = style_map.get(winobj.prompt_style.currentIndex(), 'default')

        ttsmodel = winobj.ttsmodel.currentText()
        params["gemini_ttsmodel"] = ttsmodel



        params.save()
        winobj.close()

    def setallmodels():
        t = winobj.edit_allmodels.toPlainText().strip().replace('，', ',').rstrip(',')
        current_text = winobj.model.currentText()
        winobj.model.clear()
        winobj.model.addItems([x for x in t.split(',') if x.strip()])
        if current_text:
            winobj.model.setCurrentText(current_text)
        settings['gemini_model'] = t
        settings.save()



    from videotrans.component.set_form import GeminiForm

    winobj = GeminiForm()
    app_cfg.child_forms['gemini'] = winobj
    winobj.update_ui()
    winobj.set_gemini.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.edit_allmodels.textChanged.connect(setallmodels)
    winobj.show()
