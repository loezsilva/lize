getAnnotationsList(annotations = []) {
    this.annotationsList = []
    
    if(this.selectedQuestion) {

        if(!annotations.length) {
            if(this.selectedApplicationStudent && this.selectedApplicationStudent.answers && this.selectedApplicationStudent.answers.length) {
                if(this.selectedApplicationStudent.answers.at(0).img_annotations.length) {
                    annotations = this.selectedApplicationStudent.answers.at(0).img_annotations
                }
            } else {
                if(this.selectedQuestion.img_annotations && this.selectedQuestion.img_annotations.length) {
                    annotations = this.selectedQuestion.img_annotations
                }
            }
        }

        annotations.forEach((annotation) => {
            let obj = {
                id: annotation.id,
                comments: [],
                tags: [],
            }
            annotation.body.forEach((body) => {
                if(body.purpose == "commenting")
                    obj.comments.push(body.value)
                if(body.purpose == "tagging") {
                    obj.tags.push(body.value)
                }
            })
            this.annotationsList.push(obj)
        })
    } else {
        return []
    }
},
showAnnotorious(close = false, readOnly = false, imgUrl = this.selectedQuestion.file_answer_url, modalName = "detailModal") {
    $(`#${modalName}`).modal('hide')
    
    if(this.viewer) {
        this.viewer.forceRedraw()
        this.viewer.destroy()
        if(close) {
            this.viewer.close()
            $('.overlay').addClass('d-none')
            $(`#${modalName}`).modal('show')
            this.viewer = ''
            return
        }
    }
    $('.overlay').removeClass('d-none')
    this.getAnnotationsList()
    this.viewer = new OpenSeadragon.Viewer({
        id: "img-content",
        showRotationControl: true,
        toolbar: "toolbarDiv",
        homeButton : "home",
        zoomInButton : "zoom-in",
        zoomOutButton : "zoom-out",
        rotateLeftButton: "rotate-left",
        rotateRightButton: "rotate-right",
        fullPageButton : "full-page",
        prefixUrl: "https://cdn.jsdelivr.net/npm/openseadragon@3.0/build/openseadragon/images/",
        tileSources: {
            type: "image",
            url: `${imgUrl}`,
        }
    });
    var formatter = function(annotation) {
        let error = []
        let warning = []

        annotation.bodies.forEach(function(body) {
            if(body.purpose == "tagging" && body.value.toLowerCase() == "erro") {
                error.push(body.value)
            }
            if(body.purpose == "tagging" && body.value.toLowerCase() == "atenção") {
                warning.push(body.value)
            }
        });
        if(error.length > 0) 
            return {
                'style': 'stroke-width: 3; stroke: red'
            }
        if(warning.length > 0) 
            return {
                'style': 'stroke-width: 3; stroke: yellow'
            }
            
    }
    this.anno = OpenSeadragon.Annotorious(this.viewer, {
        readOnly: readOnly,
        locale: 'auto',
        formatter: formatter,
    });

    if(this.selectedApplicationStudent && this.selectedApplicationStudent.answers && this.selectedApplicationStudent.answers.length) {
        if(this.selectedApplicationStudent.answers.at(0).img_annotations.length) {
            this.anno.setAnnotations(this.selectedApplicationStudent.answers.at(0).img_annotations)
        }
    } else {
        if(this.selectedQuestion.img_annotations && this.selectedQuestion.img_annotations.length) {
            this.anno.setAnnotations(this.selectedQuestion.img_annotations)
        }
    }

    this.anno.on('createAnnotation', (annotation) => {
        this.updateAnnotations(this.anno.getAnnotations())

        if(this.selectedApplicationStudent && this.selectedApplicationStudent.answers && this.selectedApplicationStudent.answers.length) {
            this.selectedApplicationStudent.answers.at(0).img_annotations = this.anno.getAnnotations()
        } else {
            this.selectedQuestion.img_annotations = this.anno.getAnnotations()
        }
        this.getAnnotationsList(this.anno.getAnnotations())
    })
    this.anno.on('updateAnnotation', (annotation) => {
        this.updateAnnotations(this.anno.getAnnotations())
        this.getAnnotationsList(this.anno.getAnnotations())
        if(this.selectedApplicationStudent && this.selectedApplicationStudent.answers && this.selectedApplicationStudent.answers.length) {
            this.selectedApplicationStudent.answers.at(0).img_annotations = this.anno.getAnnotations()
        } else {
            this.selectedQuestion.img_annotations = this.anno.getAnnotations()
        }
        this.getAnnotationsList(this.anno.getAnnotations())
    })
    this.anno.on('deleteAnnotation', (annotation) => {
        this.updateAnnotations(this.anno.getAnnotations())
        this.getAnnotationsList(this.anno.getAnnotations())
        if(this.selectedApplicationStudent && this.selectedApplicationStudent.answers && this.selectedApplicationStudent.answers.length) {
            if (!this.anno.getAnnotations().length) {
                this.selectedApplicationStudent.answers.at(0).img_annotations = []
            } else {
                this.selectedApplicationStudent.answers.at(0).img_annotations = this.anno.getAnnotations()
            }
        } else {
            if(this.selectedQuestion.img_annotations) {
                if (!this.anno.getAnnotations().length) {
                    this.selectedQuestion.img_annotations = []
                } else {
                    this.selectedQuestion.img_annotations = this.anno.getAnnotations()
                }
            }
        }
        this.getAnnotationsList(this.anno.getAnnotations())
    })

}

{% if user.user_type == 'coordination' or user.user_type == 'teacher' %}
, getBadgeColor(tag) {
    switch(tag.toLowerCase()) {
        case 'atenção':
            return 'badge-warning'
        case 'erro':
            return 'badge-danger'
        default:
            return 'badge-secondary'
    }
},
createTagInAnnotation(tag, annotation) {
    this.anno.getSelected().body.push({
        type: 'TextualBody',
        purpose: 'tagging',
        value: tag
    })
    this.anno.selectAnnotation(annotation.id)
},
updateAnnotations(annotations) {
    if(this.selectedApplicationStudent && this.selectedApplicationStudent.answers && this.selectedApplicationStudent.answers.length) {
        fileAnswerID = this.selectedApplicationStudent.answers.at(0).id
    } else {
        fileAnswerID = this.selectedQuestion.file_answer
    }
    let url = "{% url 'answers:api_fileanswer_annotations_create_or_update' pk='00000000-0000-0000-0000-000000000000'  %}"
    axios.put(url.replace('00000000-0000-0000-0000-000000000000', fileAnswerID), { img_annotations: annotations.length > 0 ? annotations : [] })
}

{% endif %}