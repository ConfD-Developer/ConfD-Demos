#!/usr/bin/env groovy
/*
  Install groovy and run this script `groovy UmlGenerator.groovy` to generate UML diagrams
 */
@Grab(group = 'net.sourceforge.plantuml', module = 'plantuml', version = '1.2021.2')
@Grab(group = 'org.bitbucket.novakmi', module = 'nodebuilder', version = '1.1.1')
@Grab(group = 'org.bitbucket.novakmi', module = 'plantumlbuilder', version = '1.0.0')
import org.bitbucket.novakmi.plantumlbuilder.PlantUmlBuilder
import org.bitbucket.novakmi.plantumlbuilder.PlantUmlBuilderCompPlugin
import org.bitbucket.novakmi.plantumlbuilder.PlantUmlBuilderSeqPlugin

class PumlGenerator {

    static def makeBuilder() {
        def builder = new PlantUmlBuilder()
        builder.registerPlugin(new PlantUmlBuilderSeqPlugin())
        // add extra support for Seq. diagrams
        builder.registerPlugin(new PlantUmlBuilderCompPlugin())
        // add extra support for component. diagrams
        return builder
    }

    static def makeComponentHeader(builder) {
        builder.plantuml {
            UmlCommon.makeHeader(builder, 'ConfDGnmiAdapter interaction scenario', [skipList: [UmlCommon.user]])
        }
    }

    static void main(String[] args) {
        def builder = makeBuilder()
        [
                [fileName: 'subscribeonce', txt: true, fn: Subscriber.&makeSubscriberOnceSeq],
                [fileName: 'subscribepoll', txt: true, fn: Subscriber.&makeSubscriberPollSeq],
                [fileName: 'subscribestream', txt: true, fn: Subscriber.&makeSubscriberStreamSeq],
                [fileName: 'subscribedpstream', txt: true, fn: Subscriber.&makeSubscriberDpStreamSeq]
        ].each { it ->
            builder.reset()
            print "Processing  ${it.fileName}"
            it.fn(builder)
            def text = builder.getText()
            if (it.txt) {
                new File("./${it.fileName}.puml").write(text)
            }
            println " ... done."

        }
    }
}
