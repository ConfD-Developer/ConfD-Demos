// This class contains reusable parts
class UmlCommon {
    public static def user = 'user'
    public static def client = 'client'
    public static def client_stub = 'Stub'
    public static def sub_read = 'sub_read'
    public static def server = 'server'
    public static def adapter = 'adapter'
    public static def device_adapter = 'device_adapter'
    public static def device = 'device'
    public static def dataprovider = 'dataprovider'
    public static def arrowReturn = '-->'
    public static def arrowBi = '<-->'

    private static def colorBoxGnmi = '#FFEB99'
    private static def colorBoxUser = '#Gold'
    private static def colorBoxAdapter = '#E6F3F8'
    private static def colorBoxDevice = '#FFEB99'

    static def makeHeader(builder, text, params = null) {
        builder.plant('hide footbox')
        builder.autonumber()
        builder.title(text)
        makeSkin(builder)
        makeParticipants(builder, params)
    }

    static def makeSkin(builder) {
        // list of skinparams java -jar ~/.groovy/grapes/net.sourceforge.plantuml/plantuml/jars/plantuml-1.2017.18.jar -language
        builder.plant("skinparam BackgroundColor #FFFFFF-#EEEBDC")
        builder.plant("skinparam SequenceParticipantBackgroundColor #FFFFFF-#DDEBDC")
        builder.plant("skinparam DatabaseBackgroundColor #FFFFFF-#DDEBDC")
        builder.plant("skinparam SequenceBoxFontStyle plain")
        builder.plant("skinparam SequenceGroupFontStyle plain")
        builder.plant("skinparam SequenceDividerFontStyle plain")
    }

    static def makeParticipants(builder, params = null) {
        def skipList = []

        if (params) {
            if (params?.skipList) {
                skipList = params.skipList
            }
        }

        if (!skipList.contains(user)) {
            builder.box("              <size:40><&person></size> User                  ",
                    color: colorBoxUser) {
                actor(user)
            }
        }

        builder.box("    gNMI Adapter client    ", color: colorBoxGnmi) {
            if (!skipList.contains(client)) {
                participant(client, as: '" <size:20><&terminal></size> gNMI Client "')
            }
            if (!skipList.contains(sub_read)) {
                participant(sub_read, as: '"Subscription reader\\nthread "')
            }

        }
        builder.box("    gNMI Adapter server     ", color: colorBoxAdapter) {
            if (!skipList.contains(server)) {
                participant(server, as: '" <size:20><&wrench></size> gNMI Server "')
            }
            if (!skipList.contains(adapter)) {
                participant(adapter, as: '" <size:20><&list></size>  gNMI Adapter "')
            }
            if (!skipList.contains(device_adapter)) {
                participant(device_adapter, as: '" <size:20><&list></size>  gNMI Device Adapter\\n(ConfD Adapter) "')
            }
        }
        builder.box("    Device     ", color: colorBoxDevice) {
            if (!skipList.contains(device)) {
                participant(device, as: '" <size:20><&tablet></size> ConfD\\n(device) "')
            }
            if (!skipList.contains(dataprovider)) {
                participant(dataprovider, as: '" <size:20><&tablet></size> ConfD\\nData provider"')
            }
        }
    }
}